# -*- coding: utf-8 -*-
"""
Admin Data Export Endpoint
Exports all persistent data as ZIP for migration purposes
"""

import os
import io
import zipfile
from datetime import datetime
from flask import session, send_file, jsonify
from app.routes.admin import admin_bp
from app.services.data_persistence import data_persistence


def require_admin():
    """Check if user is admin"""
    user = session.get("user")
    admin_users = os.getenv("ADMIN_USERS", "Admin").split(",")

    if not user or user not in admin_users:
        return False
    return True


@admin_bp.route("/export-all-data")
def export_all_data():
    """
    Export all persistent data as ZIP file
    Only accessible by admin users

    Returns:
        ZIP file with all JSON files from data/persistent/
    """
    # Security check
    if not require_admin():
        return jsonify({
            "error": "Unauthorized",
            "message": "Admin access required"
        }), 403

    try:
        # Get persistent data directory
        persist_dir = data_persistence.get_persist_path()

        if not os.path.exists(persist_dir):
            return jsonify({
                "error": "Data directory not found",
                "path": persist_dir
            }), 404

        # Create in-memory ZIP file
        memory_file = io.BytesIO()

        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all JSON files from persistent directory
            file_count = 0
            for root, dirs, files in os.walk(persist_dir):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        # Archive name is relative to persist_dir
                        arcname = os.path.relpath(file_path, persist_dir)
                        zipf.write(file_path, arcname)
                        file_count += 1

        # Seek to beginning of file
        memory_file.seek(0)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"business-hub-data-export_{timestamp}.zip"

        # Send file
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({
            "error": "Export failed",
            "message": str(e)
        }), 500


@admin_bp.route("/export-info")
def export_info():
    """
    Get information about exportable data
    """
    # Security check
    if not require_admin():
        return jsonify({
            "error": "Unauthorized"
        }), 403

    try:
        persist_dir = data_persistence.get_persist_path()

        if not os.path.exists(persist_dir):
            return jsonify({
                "error": "Data directory not found",
                "path": persist_dir
            }), 404

        # Collect file information
        files = []
        total_size = 0

        for root, dirs, filenames in os.walk(persist_dir):
            for filename in filenames:
                if filename.endswith('.json'):
                    filepath = os.path.join(root, filename)
                    filesize = os.path.getsize(filepath)
                    total_size += filesize

                    files.append({
                        "name": filename,
                        "size": filesize,
                        "size_kb": round(filesize / 1024, 2),
                        "modified": datetime.fromtimestamp(
                            os.path.getmtime(filepath)
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    })

        return jsonify({
            "persist_dir": persist_dir,
            "file_count": len(files),
            "total_size_bytes": total_size,
            "total_size_kb": round(total_size / 1024, 2),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "files": sorted(files, key=lambda x: x['name'])
        })

    except Exception as e:
        return jsonify({
            "error": "Failed to get export info",
            "message": str(e)
        }), 500
