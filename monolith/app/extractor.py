from bs4 import BeautifulSoup


def extract(html: str, url: str) -> dict:
    clean_text = None
    try:
        import trafilatura

        extracted = trafilatura.extract(html, url=url)
        if extracted:
            clean_text = extracted.strip()
    except Exception:
        clean_text = None

    soup = BeautifulSoup(html, "lxml")
    if not clean_text:
        paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
        clean_text = "\n\n".join([p for p in paragraphs if p])
        clean_text = clean_text.strip()

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()

    author = None
    og_author = soup.find("meta", property="og:author")
    if og_author and og_author.get("content"):
        author = og_author["content"].strip()
    elif soup.find("meta", attrs={"name": "author"}):
        author = soup.find("meta", attrs={"name": "author"}).get("content", "").strip()

    publish_date = None
    og_date = soup.find("meta", property="og:article:published_time")
    if og_date and og_date.get("content"):
        publish_date = og_date["content"].strip()
    elif soup.find("meta", attrs={"name": "date"}):
        publish_date = soup.find("meta", attrs={"name": "date"}).get("content", "").strip()

    language = None
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        language = html_tag.get("lang").strip()

    return {
        "clean_text": clean_text or "",
        "title": title,
        "author": author,
        "publish_date": publish_date,
        "language": language,
    }
