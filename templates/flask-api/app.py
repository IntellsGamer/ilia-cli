from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'change-me-in-production'

items = []

@app.route('/')
def index():
    return jsonify({
        "project": "{{ project_name }}",
        "version": "{{ version }}",
        "endpoints": {
            "GET /items": "List all items",
            "POST /items": "Create item",
            "GET /items/<id>": "Get item",
            "PUT /items/<id>": "Update item",
            "DELETE /items/<id>": "Delete item",
        }
    })

@app.route('/items', methods=['GET'])
def get_items():
    return jsonify(items)

@app.route('/items', methods=['POST'])
def create_item():
    data = request.get_json()
    item = {
        "id": len(items) + 1,
        "name": data.get("name"),
        "description": data.get("description"),
    }
    items.append(item)
    return jsonify(item), 201

@app.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    item = next((i for i in items if i["id"] == item_id), None)
    if item is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(item)

@app.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.get_json()
    for item in items:
        if item["id"] == item_id:
            item.update(data)
            return jsonify(item)
    return jsonify({"error": "Not found"}), 404

@app.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    global items
    items = [i for i in items if i["id"] != item_id]
    return jsonify({"message": "Deleted"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port={{ port }})
