"""Scrapes PSE Edge (edge.pse.com.ph) for disclosures and their PDF attachments.

PSE Edge has no public API. The disclosure list is loaded by POSTing to
/financialReports/search.ax (an AJAX endpoint the site's own JS calls), and
individual PDF attachments are fetched by POSTing a file_id to
/downloadFile.do. Both were discovered by inspecting the live site's HTML/JS.
"""

import html
import json
import re
from datetime import date, datetime, timedelta

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://edge.pse.com.ph"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def new_session():
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def get_latest_financial_reports(limit=10, lookback_days=30):
    """Returns the most recent financial report disclosures (these reliably
    carry a PDF attachment, unlike general disclosure notices which are often
    inline HTML only).
    """
    session = new_session()
    session.get(f"{BASE_URL}/financialReports/form.do")

    to_date = datetime.now()
    from_date = to_date - timedelta(days=lookback_days)

    response = session.post(
        f"{BASE_URL}/financialReports/search.ax",
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{BASE_URL}/financialReports/form.do",
        },
        data={
            "pageNo": "1",
            "companyId": "",
            "keyword": "",
            "sortType": "date",
            "dateSortType": "DESC",
            "cmpySortType": "",
            "fromDate": from_date.strftime("%m-%d-%Y"),
            "toDate": to_date.strftime("%m-%d-%Y"),
        },
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("table.list tbody tr")

    disclosures = []
    for row in rows[:limit]:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        company_link = cells[0].find("a")
        template_link = cells[1].find("a")
        if not company_link or not template_link:
            continue

        edge_no_match = re.search(r"openPopup\('([a-f0-9]+)'\)", template_link.get("onclick", ""))
        if not edge_no_match:
            continue

        disclosures.append(
            {
                "company": company_link.get_text(strip=True),
                "template_name": template_link.get_text(strip=True),
                "pse_form_number": cells[2].get_text(strip=True),
                "announce_datetime": cells[3].get_text(strip=True),
                "report_number": cells[4].get_text(strip=True),
                "edge_no": edge_no_match.group(1),
            }
        )

    return disclosures, session


def get_pdf_attachment(edge_no, session=None):
    """Given an edge_no, returns (file_id, filename) for the first attachment,
    or None if the disclosure has no attachment.
    """
    session = session or new_session()

    response = session.get(
        f"{BASE_URL}/openDiscViewer.do",
        params={"edge_no": edge_no},
        headers={"Referer": f"{BASE_URL}/financialReports/form.do"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    file_select = soup.find("select", id="file_list")
    if not file_select:
        return None

    options = [opt for opt in file_select.find_all("option") if opt.get("value")]
    if not options:
        return None

    file_id = options[0]["value"]
    filename = options[0].get_text(strip=True)
    return file_id, filename


def get_main_document_text(edge_no, session=None):
    """Returns (text, html) for the disclosure's Main Document (the
    standardized HTML cover sheet PSE renders in the viewer's iframe). Unlike
    attachments, this is always real HTML -- never a scanned image -- and for
    financial reports it includes a Balance Sheet / Income Statement summary.
    Returns ("", "") if the document has no viewable Main Document.
    """
    session = session or new_session()

    response = session.get(
        f"{BASE_URL}/openDiscViewer.do",
        params={"edge_no": edge_no},
        headers={"Referer": f"{BASE_URL}/financialReports/form.do"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    iframe = soup.find("iframe", id="viewContents")
    if not iframe:
        return "", ""

    file_id_match = re.search(r"file_id=(\d+)", iframe.get("src", ""))
    if not file_id_match:
        return "", ""

    doc_response = session.get(
        f"{BASE_URL}/downloadHtml.do",
        params={"file_id": file_id_match.group(1)},
        headers={"Referer": f"{BASE_URL}/openDiscViewer.do?edge_no={edge_no}"},
    )
    doc_response.raise_for_status()

    html = doc_response.text
    doc_soup = BeautifulSoup(html, "html.parser")
    return doc_soup.get_text(separator="\n", strip=True), html


def get_company_directory(session=None):
    """Returns every PSE-listed company from the Company Directory:
    {company, symbol, sector, subsector, listing_date}. Paginates until the
    reported total page count is exhausted.
    """
    session = session or new_session()
    session.get(f"{BASE_URL}/companyDirectory/form.do")

    companies = []
    page_no = 1
    total_pages = 1

    while page_no <= total_pages:
        response = session.post(
            f"{BASE_URL}/companyDirectory/search.ax",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{BASE_URL}/companyDirectory/form.do",
            },
            data={
                "pageNo": str(page_no),
                "companyId": "",
                "keyword": "",
                "sortType": "cmpy",
                "cmpySortType": "ASC",
                "sector": "ALL",
                "subsector": "ALL",
            },
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        count_match = re.search(r"\[\s*\d+\s*/\s*(\d+)\s*\]", soup.get_text())
        if count_match:
            total_pages = int(count_match.group(1))

        rows = soup.select("table.list tbody tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            link = cells[0].find("a")
            cmpy_id_match = re.search(r"cmDetail\('(\d+)'", link.get("onclick", "")) if link else None

            companies.append(
                {
                    "company": cells[0].get_text(strip=True),
                    "symbol": cells[1].get_text(strip=True),
                    "sector": cells[2].get_text(strip=True),
                    "subsector": cells[3].get_text(strip=True),
                    "listing_date": cells[4].get_text(strip=True),
                    "cmpy_id": cmpy_id_match.group(1) if cmpy_id_match else None,
                }
            )

        page_no += 1

    return companies


def get_stock_data(cmpy_id, session=None):
    """Returns current trading data for a company from its Stock Data page:
    last_traded_price, change, percent_change, volume, high, low,
    market_cap. Returns None if the page has no trading data (e.g. never
    traded, suspended).
    """
    session = session or new_session()

    response = session.get(
        f"{BASE_URL}/companyPage/stockData.do",
        params={"cmpy_id": cmpy_id},
        headers={"Referer": f"{BASE_URL}/companyDirectory/form.do"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    fields = {}
    for row in soup.select("table.view tr"):
        headers = row.find_all("th")
        cells = row.find_all("td")
        for th, td in zip(headers, cells):
            fields[th.get_text(strip=True)] = td.get_text(strip=True)

    last_traded_price = fields.get("Last Traded Price", "")
    volume = fields.get("Volume", "")
    change_field = fields.get("Change(% Change)", "")

    if not last_traded_price or not change_field:
        return None

    change_match = re.search(r"(up|down)\s*([\d,]+\.?\d*)\s*\(\s*([\d.]+)\s*%\)", change_field)
    if not change_match:
        return None

    direction, change_amount, percent_change = change_match.groups()
    sign = 1 if direction == "up" else -1

    try:
        price = float(last_traded_price.replace(",", ""))
        volume_int = int(volume.replace(",", "")) if volume else 0
    except ValueError:
        return None

    return {
        "price": price,
        "change": sign * float(change_amount.replace(",", "")),
        "percent_change": sign * float(percent_change),
        "volume": volume_int,
        "high": fields.get("High", ""),
        "low": fields.get("Low", ""),
        "market_cap": fields.get("Market Capitalization", ""),
    }


def get_company_logo_url(cmpy_id, session=None):
    """Returns the absolute URL of a company's logo image, scraped from its
    Stock Data page (the same page get_stock_data() fetches -- PSE Edge
    embeds the logo there as <img src="/clogo/{cmpy_id}/{filename}.png">).
    Returns None if the page has no such image.
    """
    session = session or new_session()

    response = session.get(
        f"{BASE_URL}/companyPage/stockData.do",
        params={"cmpy_id": cmpy_id},
        headers={"Referer": f"{BASE_URL}/companyDirectory/form.do"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    logo_img = soup.select_one("img[src*='/clogo/']")
    if not logo_img:
        return None

    return f"{BASE_URL}{logo_img['src']}"


def download_image(url, dest_path, session=None):
    """Downloads the image at url to dest_path."""
    session = session or new_session()

    response = session.get(url)
    response.raise_for_status()

    with open(dest_path, "wb") as f:
        f.write(response.content)

    return dest_path


def download_pdf(file_id, dest_path, edge_no, session=None):
    """Downloads the attachment for file_id to dest_path."""
    session = session or new_session()

    response = session.post(
        f"{BASE_URL}/downloadFile.do",
        data={"file_id": file_id},
        headers={"Referer": f"{BASE_URL}/openDiscViewer.do?edge_no={edge_no}"},
    )
    response.raise_for_status()

    with open(dest_path, "wb") as f:
        f.write(response.content)

    return dest_path


ICON_EVENT_TYPES = {
    "icon_srd.gif": "SRO Ex-Date",
    "icon_cd.gif": "Cash Ex-Date",
    "icon_std.gif": "Stock Ex-Date",
    "icon_pd.gif": "Property Ex-Date",
    "icon_smd.gif": "Stockholders' Meeting",
    "icon_abd.gif": "Analysts' Briefing",
    "icon_edd.gif": "ETF Dividend Ex-Date",
    "icon_srl.gif": "SRO Listing",
    "icon_srs.gif": "SRO Start",
    "icon_sre.gif": "SRO End",
    "icon_ofs.gif": "Offer Start",
    "icon_ofe.gif": "Offer End",
    "icon_ld.gif": "Listing Date",
    "icon_eos.gif": "ETF Offer Start",
    "icon_eoe.gif": "ETF Offer End",
    "icon_wed.gif": "Warrant Exp Date",
}


def get_market_calendar(year, month, session=None):
    """Returns the PSE Market Calendar events for the given year/month:
    a list of {date (ISO), event_type, company, popup_id}.
    """
    session = session or new_session()

    response = session.get(
        f"{BASE_URL}/companyPage/marketCalendar.do",
        params={"year": year, "month": month},
        headers={"Referer": f"{BASE_URL}/companyPage/marketCalendar.do"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("#calendarTb table tbody tr")

    events = []
    for row in rows:
        for cell in row.find_all("td"):
            if not cell.contents:
                continue
            day_text = cell.contents[0].strip()
            if not day_text.isdigit():
                continue
            day = int(day_text)

            for img in cell.find_all("img"):
                icon_name = img["src"].rsplit("/", 1)[-1]
                link = img.find_next_sibling("a")
                if not link:
                    continue
                popup_match = re.search(r"openPopup\('([a-f0-9]+)'\)", link.get("onclick", ""))
                events.append(
                    {
                        "date": date(year, month, day).isoformat(),
                        "event_type": ICON_EVENT_TYPES.get(icon_name, icon_name),
                        "company": link.get_text(strip=True),
                        "popup_id": popup_match.group(1) if popup_match else None,
                    }
                )

    return events


def get_dividends_and_rights(session=None):
    """Returns every current PSE cash/stock/property dividend declaration:
    {company, cmpy_id, security_type, dividend_type, dividend_rate,
    ex_dividend_date, record_date, payment_date, circular_number, edge_no}.
    Paginates until PSE Edge's own reported page count is exhausted.
    """
    session = session or new_session()
    session.get(f"{BASE_URL}/disclosureData/dividends_and_rights_info_form.do")

    entries = []
    page_num = 1
    total_pages = 1

    while page_num <= total_pages:
        response = session.post(
            f"{BASE_URL}/disclosureData/dividends_and_rights_info_list.ax",
            params={"DividendsOrRights": "Dividends"},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{BASE_URL}/disclosureData/dividends_and_rights_info_form.do",
            },
            data={
                "pageNum": str(page_num),
                "sortMode": "date",
                "dateSortType": "DESC",
                "cmpySortType": "ASC",
            },
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        count_match = re.search(r"\[\s*\d+\s*/\s*(\d+)\s*\]", soup.get_text())
        if count_match:
            total_pages = int(count_match.group(1))

        rows = soup.select("table.list tbody tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 8:
                continue

            company_link = cells[0].find("a")
            circular_link = cells[7].find("a")
            edge_no_match = (
                re.search(r"openPopup\('([a-f0-9]+)'\)", circular_link.get("onclick", ""))
                if circular_link else None
            )
            cmpy_id_match = (
                re.search(r"cmpy_id=(\d+)", company_link.get("href", ""))
                if company_link else None
            )

            entries.append(
                {
                    "company": company_link.get_text(strip=True) if company_link else cells[0].get_text(strip=True),
                    "cmpy_id": cmpy_id_match.group(1) if cmpy_id_match else None,
                    "security_type": cells[1].get_text(strip=True),
                    "dividend_type": cells[2].get_text(strip=True),
                    "dividend_rate": cells[3].get_text(strip=True),
                    "ex_dividend_date": cells[4].get_text(strip=True),
                    "record_date": cells[5].get_text(strip=True),
                    "payment_date": cells[6].get_text(strip=True),
                    "circular_number": circular_link.get_text(strip=True) if circular_link else cells[7].get_text(strip=True),
                    "edge_no": edge_no_match.group(1) if edge_no_match else None,
                }
            )

        page_num += 1

    return entries


def get_index_snapshot(session=None):
    """Returns live last-trade data for every PSE security in one request:
    {symbol, company, sector_codes, last_trade_price, last_trade_date,
    outstanding_shares}. sector_codes includes "PSEI" for the 30 official
    PSEi index constituents.
    """
    session = session or new_session()
    response = session.get("https://frames.pse.com.ph/indices")
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    store_json = soup.find("input", id="store-json")
    if not store_json:
        return []

    raw = html.unescape(store_json.get("value", ""))
    data = json.loads(raw) if raw else []

    return [
        {
            "symbol": d.get("Symbol"),
            "company": d.get("SecurityName"),
            "sector_codes": d.get("SectorCode", []),
            "last_trade_price": d.get("LastTradePrice"),
            "last_trade_date": d.get("LastTradeDate"),
            "outstanding_shares": d.get("OutstandingShares"),
        }
        for d in data
    ]


def get_psei_constituents(session=None):
    """Returns the 30 current official PSEi index constituent symbols."""
    return [d["symbol"] for d in get_index_snapshot(session=session) if "PSEI" in d["sector_codes"]]


def get_movers_snapshot(session=None):
    """Returns PSE's own pre-computed top-10 most-active/gainers/losers
    from frames.pse.com.ph's homepage: {"most_active": [...], "gainers":
    [...], "losers": [...]}, each entry {symbol, value, price, change,
    percent_change}, already correctly ordered by PSE.
    """
    session = session or new_session()
    response = session.get("https://frames.pse.com.ph/")
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    def _parse_table(table_id):
        div = soup.find("div", id=table_id)
        if not div:
            return []
        results = []
        for row in div.select("tbody tr"):
            cells = row.find_all("td")
            link = row.find("a")
            if not link or len(cells) < 5:
                continue
            results.append(
                {
                    "symbol": link.get_text(strip=True),
                    "value": cells[1].get_text(strip=True),
                    "price": cells[2].get_text(strip=True),
                    "change": cells[3].get_text(strip=True),
                    "percent_change": cells[4].get_text(strip=True),
                }
            )
        return results

    return {
        "most_active": _parse_table("mostActiveTable"),
        "gainers": _parse_table("advancesTable"),
        "losers": _parse_table("declineTable"),
    }
