"""
Flask application with proper CORS configuration
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
import os

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///stories.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# CRITICAL FIX: Proper CORS configuration
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:5173"],  # Add your frontend URLs
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
})

# Import models and story generation
from models import Story
from story_generation import generate_story, create_story_record


@app.route('/api/stories', methods=['GET'])
def get_stories():
    """Get all stories"""
    try:
        stories = Story.query.order_by(Story.created_at.desc()).all()
        return jsonify([story.to_dict() for story in stories]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stories/<int:story_id>', methods=['GET'])
def get_story(story_id):
    """Get a single story by ID"""
    try:
        story = Story.query.get(story_id)
        if not story:
            return jsonify({'error': 'Story not found'}), 404
        return jsonify(story.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stories', methods=['POST'])
def create_story():
    """Create a new story and start generation"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('genre') or not data.get('theme'):
            return jsonify({'error': 'Genre and theme are required'}), 400
        
        # Create story record immediately
        story = create_story_record(db, data)
        
        # Start story generation in background thread
        thread = Thread(
            target=generate_story,
            args=(
                db,
                story.id,
                data.get('genre'),
                data.get('theme'),
                data.get('characters'),
                data.get('setting'),
                data.get('length', 'short')
            )
        )
        thread.daemon = True
        thread.start()
        
        # Return the story record immediately with ID
        return jsonify(story.to_dict()), 201
        
    except Exception as e:
        print(f"Error in create_story: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stories/<int:story_id>', methods=['PUT'])
def update_story(story_id):
    """Update a story"""
    try:
        story = Story.query.get(story_id)
        if not story:
            return jsonify({'error': 'Story not found'}), 404
        
        data = request.get_json()
        
        # Update fields
        if 'title' in data:
            story.title = data['title']
        if 'content' in data:
            story.content = data['content']
        if 'status' in data:
            story.status = data['status']
        
        db.commit()
        return jsonify(story.to_dict()), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/stories/<int:story_id>', methods=['DELETE'])
def delete_story(story_id):
    """Delete a story"""
    try:
        story = Story.query.get(story_id)
        if not story:
            return jsonify({'error': 'Story not found'}), 404
        
        db.session.delete(story)
        db.commit()
        return jsonify({'message': 'Story deleted successfully'}), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Create tables
    with app.app_context():
        db.create_all()
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
