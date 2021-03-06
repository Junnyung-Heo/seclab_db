from flask import request, render_template, url_for, Blueprint, Response, send_file, session
from flask_login import current_user, login_required
from web.database import db_session
from web.database.models import Query
import json


index_blueprint = Blueprint('index', __name__)


@index_blueprint.route('/', methods=['GET'])
@login_required
def index():
    return render_template('/index.html')


@index_blueprint.route('/queries', methods=['GET'])
@login_required
def get_queries():
    user_id = current_user.id
    user_queries = db_session.query(Query).filter(Query.user_id == user_id).order_by(Query.created_at).all()
    db_session.close()

    while len(user_queries) > 10:
        user_queries.remove(user_queries[0])

    response_dict = list()
    for user_query in user_queries:
        response_dict.append({
            'query_id': user_query.id,
            'query_status': user_query.status,
            'query_created_at': str(user_query.created_at)
        })
    return Response(json.dumps(response_dict), status=200)


@index_blueprint.route('/queries/<query_id>', methods=['GET'])
@login_required
def get_query_files(query_id):
    user_id = current_user.id
    query = db_session.query(Query).filter(Query.id == query_id).first()
    db_session.close()
    if not query.user_id == user_id:
        return Response(status=403)
    return send_file(query.result_path, as_attachment=True, attachment_filename="list.txt")
