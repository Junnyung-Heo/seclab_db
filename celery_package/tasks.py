from celery import Task
from celery_package import celery
from database import db_session
from database.models import Virussign, Virusshare, Kisa, Kaspersky, BitDefender, Symantec, Benign, RawFile, Query
from sqlalchemy import or_, desc, union_all
from flask_socketio import SocketIO
import datetime, settings, os


class QueryTask(Task):
    def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
                    link=None, link_error=None, shadow=None, **options):
        return super(QueryTask, self).apply_async(args=args, kwargs=kwargs, task_id=task_id, producer=producer,
                                                  link=link, link_error=link_error, shadow=shadow, **options)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        query_id = kwargs['query_id']
        _query = Query.query.filter(Query.id == query_id).first()
        _query.status = 3
        db_session.commit()
        db_session.close()
        task_socket_io = SocketIO(message_queue=kwargs['redis_url'])
        task_socket_io.emit('query_failed', namespace='/socket', room=kwargs['room'])

    def on_success(self, retval, task_id, args, kwargs):
        query_id = kwargs['query_id']
        _query = Query.query.filter(Query.id == query_id).first()
        _query.status = 2
        db_session.commit()
        db_session.close()
        task_socket_io = SocketIO(message_queue=kwargs['redis_url'])
        task_socket_io.emit('query_success', namespace='/socket', room=kwargs['room'])


@celery.task(base=QueryTask)
def search_task(file_type, channel_list, date_range, vaccine_company, label, limit, result_path, query_id, redis_url, room):

    if type(channel_list) == str:
        channel_list = [channel_list]

    partial_query_list = list()
    for channel in channel_list:
        if channel == 'virussign':
            channel_class = Virussign
        elif channel == 'virusshare':
            channel_class = Virusshare
        elif channel == 'kisa':
            channel_class = Kisa
        elif channel == 'benign-crawling':
            channel_class = Benign

        partial_query = RawFile.query.filter(RawFile.md5 == channel_class.raw_file_md5)
        if date_range:
            start_date = datetime.datetime.strptime(date_range[0], '%Y-%m-%d')
            end_date = datetime.datetime.strptime(date_range[1], '%Y-%m-%d') + datetime.timedelta(days=1)
            partial_query.filter(channel_class.collected_at >= start_date).filter(channel_class.collected_at < end_date)
        partial_query_list.append(partial_query)

    query = partial_query_list[0]
    for partial_query in partial_query_list[1:]:
        query = query.union(partial_query)
    query = query.with_entities(RawFile.md5, RawFile.path)

    if file_type == 'malware':
        if vaccine_company == 'kaspersky':
            vaccine_company = Kaspersky
        elif vaccine_company == 'bitdefender':
            vaccine_company = BitDefender
        elif vaccine_company == 'symantec':
            vaccine_company = Symantec

        query = query.join(vaccine_company)
        query = query.filter(vaccine_company.label.contains(label))

    elif file_type == 'benign':
        subquery1 = Kaspersky.query.distinct().with_entities(Kaspersky.raw_file_md5)
        subquery2 = BitDefender.query.distinct().with_entities(BitDefender.raw_file_md5)
        subquery3 = Symantec.query.distinct().with_entities(Symantec.raw_file_md5)
        query = query.filter(~RawFile.md5.in_(subquery1)).filter(~RawFile.md5.in_(subquery2)).filter(~RawFile.md5.in_(subquery3))

    if limit:
        query = query.limit(limit)
    query_results = query.all()

    _query = Query.query.filter(Query.id == query_id).first()
    _query.status = 1
    db_session.commit()
    db_session.close()

    task_socket_io = SocketIO(message_queue=redis_url)
    task_socket_io.emit('query_listing', namespace='/socket', room=room)

    f = open(os.path.join(settings.QUERY_RESULT_PATH, result_path), 'w')
    for query_result in query_results:
        f.write(query_result[1]+'\n')
    f.close()

    return True

