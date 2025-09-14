__all__ = ["get"]


# standard library
import re
from itertools import product
from logging import getLogger
from types import MappingProxyType


# dependencies
import httpx
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm


# constants
LOGGER = getLogger(__name__)
SEASONS = "a", "b"
SESSIONS = MappingProxyType(
    {
        "N": "恒星・恒星進化",
        "M": "太陽",
        "P": "星・惑星形成",
        "Q": "星間現象",
        "R": "銀河",
        "S": "活動銀河核",
        "T": "銀河団",
        "U": "宇宙論",
        "V": "観測機器",
        "W": "コンパクト天体",
        "X": "銀河形成・進化",
        "Y": "天文教育・広報普及・その他",
        "PDL": "ポストデッドライン・ペーパー",
    }
)
URL_ARCHIVE = "https://www.asj.or.jp/nenkai/archive"
URL_SESSION = re.compile(r"session-([A-Z]+[0-9]*)\.html")


def get(
    begin_year: int = 1996,
    end_year: int = 2025,
    /,
    *,
    progress: bool = True,
    timeout: float = 10.0,
) -> pd.DataFrame:
    """Get session information of the all ASJ annual meetings.

    Args:
        begin_year: The beginning year for the search range.
        end_year: The ending year for the search range.
        progress: Whether to show a progress bar.
        timeout: The timeout for HTTP requests in seconds.

    Returns:
        A DataFrame containing the session information.

    """
    dfs = []

    for year, season in tqdm(
        list(product(range(begin_year, end_year + 1), SEASONS)),
        disable=not progress,
    ):
        try:
            dfs.append(get_each(year, season, timeout=timeout))
        except httpx.HTTPError as error:
            LOGGER.warning(f"Failed to get session: {year=}, {season=}")
            continue

    return pd.concat(dfs)


def get_each(
    year: int,
    season: str,
    /,
    *,
    timeout: float = 10.0,
) -> pd.DataFrame:
    """Get session information of a specific ASJ annual meeting.

    Args:
        year: The year of the ASJ annual meeting.
        season: The season of the ASJ annual meeting.
        timeout: The timeout for HTTP requests in seconds.

    Returns:
        A DataFrame containing the session information.

    """
    resp = httpx.get(
        f"{URL_ARCHIVE}/{year}{season}/index.html",
        timeout=timeout,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content.decode(), "html.parser")
    categories, ids, names, numbers = [], [], [], []

    for tag in soup.find_all("a"):
        if (href := tag.attrs.get("href")) is None:  # type: ignore
            continue

        if match := URL_SESSION.search(str(href)):
            names.append(name := tag.get_text(strip=True))
            numbers.append(number := match.group(1))
            categories.append(to_category(name))
            ids.append(f"{year}-{season}-{number}")

    return pd.DataFrame(
        index=pd.Index(ids, name="ID"),
        data={
            "Year": year,
            "Season": season,
            "Number": numbers,
            "Category": categories,
            "Name": names,
        },
    )


def to_category(name: str, /, *, default: str = "企画セッション") -> str:
    """Infer the session category from the session name.

    Args:
        name: The name of the session.

    Returns:
        The inferred session category.

    """
    if name in SESSIONS.values():
        return name

    if "恒星" in name or "超新星爆発" in name:
        return SESSIONS["N"]

    if (
        "星・惑星形成" in name
        or name == "星形成"
        or name == "太陽系"
        or name == "天体力学"
        or name == "位置天文学"
    ):
        return SESSIONS["P"]

    if "観測機器" in name:
        return SESSIONS["V"]

    if "コンパクト天体" in name or "高密度" in name:
        return SESSIONS["W"]

    if "銀河形成" in name:
        return SESSIONS["X"]

    if "天文教育" in name:
        return SESSIONS["Y"]

    if name == "Post-deadline papers":
        return SESSIONS["PDL"]

    return default
