import os
import sqlite3
import uuid

from flask import Flask, jsonify, render_template, request
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from jd_intake_pipeline import build_graph

app = Flask(__name__)

# check_same_thread=False: Flask's dev server can serve requests on a different
# thread than the one that opened this connection.
_conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
checkpointer = SqliteSaver(_conn)
graph = build_graph(checkpointer)


def _format_result(result: dict) -> str:
    """Same summary the CLI prints, joined into one chat message."""
    lines = [f"Status: {result['status']}"] + [f"- {line}" for line in result["log"]]
    if result["status"] == "published":
        lines.append(f"Published job_id: {result['job_id']}")
    return "\n".join(lines)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    thread_id = data.get("thread_id")

    if thread_id:
        # An open thread means the pipeline is mid-pause waiting on a missing
        # field - this message is the answer, not a new submission.
        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke(Command(resume=message), config=config)
    else:
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke({"raw_jd": message}, config=config)

    if "__interrupt__" in result:
        question = result["__interrupt__"][0].value["question"]
        return jsonify({"reply": question, "thread_id": thread_id, "done": False})

    return jsonify({"reply": _format_result(result), "thread_id": None, "done": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)