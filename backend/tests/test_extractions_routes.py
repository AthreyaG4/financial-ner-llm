import io

from models import Extraction, ExtractionStatus


def _upload(client, filename="invoice.pdf", content_type="application/pdf"):
    return client.post(
        "/extractions",
        files={"file": (filename, io.BytesIO(b"%PDF-1.4 fake"), content_type)},
    )


def test_create_extraction_returns_parsing_status(client, mock_background_tasks):
    response = _upload(client)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "parsing"
    assert body["file_name"] == "invoice.pdf"
    assert body["entities"] is None


def test_create_extraction_rejects_non_pdf(client, mock_background_tasks):
    response = client.post(
        "/extractions",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400


def test_get_extraction_not_found(client):
    response = client.get("/extractions/does-not-exist")
    assert response.status_code == 404


def test_get_extraction_roundtrip(client, mock_background_tasks):
    created = _upload(client).json()
    response = client.get(f"/extractions/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_list_extractions_includes_created(client, mock_background_tasks):
    created = _upload(client).json()
    response = client.get("/extractions")
    assert response.status_code == 200
    ids = [row["id"] for row in response.json()]
    assert created["id"] in ids


def test_trigger_extraction_not_found(client):
    response = client.post("/extractions/does-not-exist/extract")
    assert response.status_code == 404


def test_trigger_extraction_rejects_when_still_parsing(client, mock_background_tasks):
    created = _upload(client).json()
    response = client.post(f"/extractions/{created['id']}/extract")
    assert response.status_code == 409


def test_trigger_extraction_succeeds_when_parsed(
    client, mock_background_tasks, db_session
):
    created = _upload(client).json()
    row = db_session.get(Extraction, created["id"])
    row.status = ExtractionStatus.PARSED
    db_session.commit()

    response = client.post(f"/extractions/{created['id']}/extract")
    assert response.status_code == 202
    assert response.json()["status"] == "extracting"
