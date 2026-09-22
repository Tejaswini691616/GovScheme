# PATH: GovScheme/routes/notification_routes.py
from flask import Blueprint, render_template, redirect, url_for, session

from routes.auth_routes import login_required
from models.notification_model import get_notifications_for_user, mark_as_read, mark_all_as_read

notification_bp = Blueprint("notification", __name__)


@notification_bp.route("/notifications")
@login_required
def notifications_list():
    notifications = get_notifications_for_user(session["user_id"])
    return render_template("notifications/notifications.html", notifications=notifications)


@notification_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def read_notification(notification_id):
    mark_as_read(notification_id, session["user_id"])
    return redirect(url_for("notification.notifications_list"))


@notification_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def read_all_notifications():
    mark_all_as_read(session["user_id"])
    return redirect(url_for("notification.notifications_list"))
