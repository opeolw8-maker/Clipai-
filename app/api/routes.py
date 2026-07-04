"""
HTTP layer only: parse the request, call a service, shape the response.
"""
import os
import uuid

from flask import Blueprint, current_app, jsonify, render_template, request, send_from_directory

from app.api.schemas import parse_clip_request
from app.services.upload_service import UploadValidationError

bp = Blueprint("clipai", __name__)


def _container():
    return current_app.config["CONTAINER"]


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/health")
def health():
    return jsonify({"status": "ok"})


@bp.route("/upload", methods=["POST"])
def upload():
    container = _container()
    config = container.config
    try:
        video_url = request.form.get("video_url", "")
        file = request.files.get("video")
        if not file:
            return jsonify({"error": "No video file provided. Please upload a video file."}), 400

        options = parse_clip_request(request.form)

        job_id = str(uuid.uuid4())[:8]
        job_dir = os.path.join(config.output_folder, job_id)
        os.makedirs(job_dir, exist_ok=True)

        if video_url:
            return jsonify({
                "error": "URL downloading is not supported. Please download your video from "
                         "YouTube, TikTok or Instagram first, then upload the file directly."
            }), 400

        try:
            video_path = container.upload_service.save(file, job_id)
        except UploadValidationError as e:
            return jsonify({"error": str(e)}), 400

        container.jobs.create(job_id)
        container.job_executor.submit(job_id, video_path, job_dir, options)
        return jsonify({"job_id": job_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/status/<job_id>")
def status(job_id):
    job = _container().jobs.get(job_id)
    if job is None:
        return jsonify({"status": "error", "message": "Job not found"}), 404
    return jsonify(job.to_dict())


@bp.route("/download/<job_id>/<filename>")
def download_clip(job_id, filename):
    config = _container().config
    job_dir = os.path.join(config.output_folder, job_id)
    if not os.path.exists(os.path.join(job_dir, filename)):
        return jsonify({"error": "File not found — please regenerate"}), 404
    return send_from_directory(job_dir, filename, as_attachment=True, download_name=filename)
