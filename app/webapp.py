"""QA webapp for reviewing PlotCaptions."""

import os

from flask import Flask, jsonify, render_template, request, send_from_directory
from pymongo import MongoClient

app = Flask(__name__)

CLIENT = MongoClient()
COLL = CLIENT["plotqa"]["captions"]
PNG_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "data", "pngs")


def _random_doc(max_tries=10):
    """Return a random document that hasn't been reviewed yet."""
    for _ in range(max_tries):
        docs = list(COLL.aggregate([{"$sample": {"size": 1}}]))
        if not docs:
            return None
        if "qa_ok" not in docs[0]:
            return docs[0]
    return docs[0]


@app.route("/")
def index():
    return render_template("index.html")


def _serialize(doc):
    return {
        "id": doc["_id"],
        "caption": doc["caption"],
        "image_index": doc["image_index"],
        "qa_ok": doc.get("qa_ok"),
    }


@app.route("/api/caption")
@app.route("/api/caption/<int:doc_id>")
def api_caption(doc_id=None):
    if doc_id is not None:
        doc = COLL.find_one({"_id": doc_id})
        if doc is None:
            return jsonify({"error": "Document not found"}), 404
    else:
        doc = _random_doc()
        if doc is None:
            return jsonify({"error": "No documents found"}), 404
    return jsonify(_serialize(doc))


@app.route("/api/mark/<int:doc_id>/<verdict>", methods=["POST"])
def api_mark(doc_id, verdict):
    if verdict not in ("correct", "incorrect"):
        return jsonify({"error": "verdict must be 'correct' or 'incorrect'"}), 400
    result = COLL.update_one(
        {"_id": doc_id},
        {"$set": {"qa_ok": verdict == "correct"}},
    )
    if result.matched_count == 0:
        return jsonify({"error": "Document not found"}), 404
    return jsonify({"status": "ok", "qa_ok": verdict == "correct"})


@app.route("/images/<int:image_index>.png")
def serve_image(image_index):
    return send_from_directory(os.path.abspath(PNG_DIR), f"{image_index}.png")


if __name__ == "__main__":
    app.run(debug=True, port=5050)
