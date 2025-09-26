from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import boto3
from boto3.dynamodb.conditions import Attr
import uuid
import os
import logging

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)

# --- AWS Configuration ---
# ⚠️ IMPORTANT: Replace these placeholders with your actual AWS keys.
AWS_ACCESS_KEY = "PASTE_YOUR_ACCESS_KEY_HERE"
AWS_SECRET_KEY = "PASTE_YOUR_SECRET_KEY_HERE"
AWS_REGION = 'us-east-1'
S3_BUCKET = 'lost-found-images-yourproject'  # 👈 Remember to replace this

# Table names
DYNAMODB_LOST_ITEMS_TABLE = 'LostItems'
DYNAMODB_FOUND_ITEMS_TABLE = 'FoundItems'
DYNAMODB_USERS_TABLE = 'UserAccounts'
DYNAMODB_ADMIN_TABLE = 'AdminAccounts'
DYNAMODB_FEEDBACK_TABLE = 'Feedback'

# --- AWS Service Clients ---
def get_aws_clients():
    try:
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
        s3_client = boto3.client('s3', region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
        return {
            's3': s3_client,
            'lost_items': dynamodb_resource.Table(DYNAMODB_LOST_ITEMS_TABLE),
            'found_items': dynamodb_resource.Table(DYNAMODB_FOUND_ITEMS_TABLE),
            'users': dynamodb_resource.Table(DYNAMODB_USERS_TABLE),
            'admins': dynamodb_resource.Table(DYNAMODB_ADMIN_TABLE),
            'feedback': dynamodb_resource.Table(DYNAMODB_FEEDBACK_TABLE)
        }
    except Exception as e:
        logging.error(f"Failed to initialize AWS clients: {e}")
        return None

# --- Main Website Route ---
@app.route('/')
def serve_app():
    return render_template('index.html')

# --- Admin Endpoints ---
@app.route('/api/admin/items', methods=['GET'])
def admin_get_all_items():
    clients = get_aws_clients()
    try:
        lost_items = clients['lost_items'].scan().get('Items', [])
        found_items = clients['found_items'].scan().get('Items', [])
        return jsonify({'status': 'success', 'items': lost_items + found_items})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/admin/users', methods=['GET'])
def admin_get_all_users():
    clients = get_aws_clients()
    try:
        users = clients['users'].scan().get('Items', [])
        # Remove passwords before sending
        for user in users:
            if 'password' in user:
                del user['password']
        return jsonify({'status': 'success', 'users': users})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/admin/feedback', methods=['GET'])
def admin_get_all_feedback():
    clients = get_aws_clients()
    try:
        feedback = clients['feedback'].scan().get('Items', [])
        return jsonify({'status': 'success', 'feedback': feedback})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/admin/matches', methods=['GET'])
def get_matches():
    clients = get_aws_clients()
    try:
        lost_items = clients['lost_items'].scan(FilterExpression=Attr('status').eq('reported')).get('Items', [])
        found_items = clients['found_items'].scan(FilterExpression=Attr('status').eq('available')).get('Items', [])
        
        match_results = []

        for lost in lost_items:
            potential_matches = []
            for found in found_items:
                # Simple matching algorithm based on shared words
                lost_text = f"{lost.get('name', '')} {lost.get('description', '')}".lower()
                found_text = f"{found.get('name', '')} {found.get('description', '')}".lower()
                
                lost_words = set(lost_text.split())
                found_words = set(found_text.split())
                
                intersection = len(lost_words.intersection(found_words))
                union = len(lost_words.union(found_words))
                
                if union > 0:
                    score = int((intersection / union) * 100)
                    if score > 10: # Only show matches with a score > 10%
                        potential_matches.append({'found_item': found, 'score': score})
            
            if potential_matches:
                potential_matches.sort(key=lambda x: x['score'], reverse=True)
                match_results.append({'lost_item': lost, 'matches': potential_matches})

        return jsonify({'status': 'success', 'match_results': match_results})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- User, Login, and Feedback Endpoints ---
@app.route('/api/signup', methods=['POST'])
def signup():
    clients, data = get_aws_clients(), request.json
    users_table = clients['users']
    try:
        if 'Item' in users_table.get_item(Key={'email': data['email']}):
            return jsonify({'status': 'error', 'message': 'User already exists.'}), 409
        user_item = {'email': data['email'], 'name': data['name'], 'collegeId': data['collegeId'], 'phoneNumber': data['phoneNumber'], 'address': data['address'], 'password': data['password'], 'id': f"user-{uuid.uuid4()}"}
        users_table.put_item(Item=user_item)
        return jsonify({'status': 'success', 'message': 'Account created.'}), 201
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    clients, data = get_aws_clients(), request.json
    users_table = clients['users']
    try:
        response = users_table.get_item(Key={'email': data['email']})
        if 'Item' not in response or response['Item']['password'] != data['password']:
            return jsonify({'status': 'error', 'message': 'Invalid credentials.'}), 401
        user = response['Item']
        del user['password']
        return jsonify({'status': 'success', 'user': user}), 200
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    clients, data = get_aws_clients(), request.json
    admin_table = clients['admins']
    try:
        response = admin_table.get_item(Key={'email': data['email']})
        if 'Item' not in response or response['Item']['password'] != data['password']:
            return jsonify({'status': 'error', 'message': 'Invalid admin credentials.'}), 401
        admin_user = response['Item']
        del admin_user['password']
        return jsonify({'status': 'success', 'user': admin_user}), 200
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    clients, data = get_aws_clients(), request.json
    feedback_table = clients['feedback']
    feedback_item = {'feedbackId': str(uuid.uuid4()), 'userEmail': data['userEmail'], 'message': data['message'], 'createdAt': data['createdAt']}
    try:
        feedback_table.put_item(Item=feedback_item)
        return jsonify({'status': 'success', 'message': 'Feedback received.'}), 201
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

# --- Item Management Endpoints ---
def upload_image_to_s3(image, item_type, item_id, s3_client):
    if not image or not image.filename: return None
    try:
        extension = os.path.splitext(image.filename)[-1]
        s3_key = f"{item_type}/{item_id}{extension}"
        s3_client.upload_fileobj(image, S3_BUCKET, s3_key)
        return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    except Exception as e:
        logging.error(f"S3 upload failed: {e}")
        return None

@app.route('/api/lost-items', methods=['POST'])
def submit_lost_item():
    clients, data = get_aws_clients(), request.form
    item_id = f"lost-{uuid.uuid4()}"
    image_url = upload_image_to_s3(request.files.get('image'), 'lost', item_id, clients['s3'])
    item_to_save = {'itemId': item_id, 'name': data.get('name'), 'description': data.get('description'), 'location': data.get('location'), 'reporterId': data.get('reporterId'), 'reporterEmail': data.get('reporterEmail'), 'createdAt': data.get('createdAt'), 'status': 'reported', 'type': 'lost', 'imageUrl': image_url}
    clients['lost_items'].put_item(Item=item_to_save)
    return jsonify({'status': 'success', 'item': item_to_save}), 201

@app.route('/api/found-items', methods=['POST'])
def submit_found_item():
    clients, data = get_aws_clients(), request.form
    image = request.files.get('image')
    if not image: return jsonify({'status': 'error', 'message': 'Image is required for found items'}), 400
    item_id = f"found-{uuid.uuid4()}"
    image_url = upload_image_to_s3(image, 'found', item_id, clients['s3'])
    item_to_save = {'itemId': item_id, 'name': data.get('name'), 'description': data.get('description'), 'location': data.get('location'), 'dropoffLocation': data.get('dropoffLocation'), 'reporterId': data.get('reporterId'), 'reporterEmail': data.get('reporterEmail'), 'createdAt': data.get('createdAt'), 'status': 'available', 'type': 'found', 'imageUrl': image_url}
    clients['found_items'].put_item(Item=item_to_save)
    return jsonify({'status': 'success', 'item': item_to_save}), 201

@app.route('/api/found-items', methods=['GET'])
def get_found_items():
    clients = get_aws_clients()
    response = clients['found_items'].scan()
    return jsonify({'status': 'success', 'items': response.get('Items', [])}), 200

@app.route('/api/my-items', methods=['GET'])
def get_my_items():
    clients, email = get_aws_clients(), request.args.get('reporterEmail')
    if not email: return jsonify({'status': 'error', 'message': 'reporterEmail is required'}), 400
    try:
        lost = clients['lost_items'].scan(FilterExpression=Attr('reporterEmail').eq(email)).get('Items', [])
        found = clients['found_items'].scan(FilterExpression=Attr('reporterEmail').eq(email)).get('Items', [])
        return jsonify({'status': 'success', 'items': lost + found})
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/items/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    clients = get_aws_clients()
    table = clients['lost_items'] if item_id.startswith('lost-') else clients['found_items']
    try:
        table.delete_item(Key={'itemId': item_id})
        return jsonify({'status': 'success', 'message': 'Item deleted.'}), 200
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/items/<item_id>/status', methods=['PUT'])
def update_item_status(item_id):
    clients, data = get_aws_clients(), request.json
    table = clients['lost_items'] if item_id.startswith('lost-') else clients['found_items']
    try:
        table.update_item(Key={'itemId': item_id}, UpdateExpression="set #st = :s", ExpressionAttributeNames={'#st': 'status'}, ExpressionAttributeValues={':s': data.get('status')})
        return jsonify({'status': 'success', 'message': 'Status updated.'}), 200
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')