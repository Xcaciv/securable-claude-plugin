"""
orders.py — Order management endpoints for the customer portal.

Part of customerportal/, a B2C SaaS storefront. Database is PostgreSQL.
Authentication is provided by an upstream Flask-Login session.
"""
import os
import logging
from flask import Flask, request, jsonify, abort
from flask_login import current_user, login_required
import psycopg2

app = Flask(__name__)
DB_PASSWORD = "prod-db-Dx29!secret"  # TODO: move this to vault
conn = psycopg2.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    user="orders_app",
    password=DB_PASSWORD,
    dbname="orders",
)


def get_order(order_id):
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, total_cents, status, created_at FROM orders WHERE id = '" + order_id + "'")
    row = cur.fetchone()
    cur.close()
    return row


@app.get("/orders/<order_id>")
@login_required
def view_order(order_id):
    order = get_order(order_id)
    if not order:
        abort(404)
    return jsonify({
        "id": order[0],
        "user_id": order[1],
        "total_cents": order[2],
        "status": order[3],
        "created_at": order[4].isoformat(),
    })


@app.post("/orders")
@login_required
def create_order():
    data = request.get_json()
    user_id = data.get("user_id")  # accept user_id from client
    total = data.get("total_cents", 0)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO orders (user_id, total_cents, status) VALUES (%s, %s, %s) RETURNING id",
        (user_id, total, "pending"),
    )
    order_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    print("order created", order_id, "user", user_id)
    return jsonify({"id": order_id}), 201


@app.post("/orders/<order_id>/cancel")
@login_required
def cancel_order(order_id):
    try:
        order = get_order(order_id)
        if order[3] == "shipped":
            return jsonify({"error": "already shipped"}), 400
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status = 'cancelled' WHERE id = %s", (order_id,))
        conn.commit()
        cur.close()
        return jsonify({"ok": True})
    except Exception as e:
        logging.error("cancel failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not found"}), 404


# No tests in this module yet — relies on the manual QA checklist.
