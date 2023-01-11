from flask import Flask, redirect, abort, request, jsonify
from flask_cors import CORS
import requests
import time
from urllib import parse
import base64
import hmac
from hashlib import sha1

app = Flask(__name__)
cors = CORS(app)
app.config['json_as_ascii'] = False  # jsonify中文
app.config['JSONIFY_MIMETYPE'] = "application/json;charset=utf-8"

douban_api_host = 'https://frodo.douban.com/api/v2'
miniapp_apikey = '0ac44ae016490db2204ce0a042db2916'
app_secret = 'bf7dddc7c9cfe6f7'
app_apikey = '0dad551ec0f84ed02907ff5c42e8ec70'


def miniapp_request(path, query):
    url = f'{douban_api_host}{path}'
    query.update({
        'apikey': miniapp_apikey
    })
    headers = {
        "Referer": "https://servicewechat.com/wx2f9b06c1de1ccfca/84/page-frame.html",
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36 MicroMessenger/7.0.9.501 NetType/WIFI MiniProgramEnv/Windows WindowsWechat"
    }
    try:
        res = requests.get(url=url, params=query, headers=headers).json()
        return res
    except Exception:
        return False


def app_sign(path, timestamp):
    raw = '&'.join(['GET', parse.quote(path, safe=''), timestamp])
    return base64.b64encode(hmac.new(app_secret.encode(), raw.encode(), sha1).digest()).decode()


def app_request(path, query):
    _ts = str(int(time.time()))
    _sig = app_sign(f'/api/v2{path}', _ts)
    url = f'{douban_api_host}{path}'
    query.update({
        's': 'rexxar_new',
        '_sig': _sig,
        '_ts': _ts,
        'apikey': app_apikey
    })
    headers = {
        'User-Agent': 'api-client/1 com.douban.frodo/7.18.0(230) Android/31 product/apollo vendor/Xiaomi model/M2007J3SC brand/Redmi  rom/miui6  network/unknown  platform/mobile'
    }
    try:
        res = requests.get(url=url, params=query, headers=headers).json()
        return res
    except Exception:
        return False


def search_suggest(wd):
    res = miniapp_request('/search/suggestion', {
        'q': wd
    })
    if res['cards']:
        return False
    return True

# 豆瓣电影/电视搜索(非聚合)
@app.route('/search/movie')
def search():
    try:
        q = request.args.get('q', type=str)
        while (len(q) >= 2) and search_suggest(q):
            q = q[:len(q) - 1]
        res = miniapp_request(request.path, {
            'q': q,
            'start': request.args.get('start', type=int),
            'count': request.args.get('count', type=int)
        })
        if not res['items']:
            abort(404)
        select_res = []
        for item in res['items']:
            select_res.append({
                'type': item['target_type'],
                'title': item['target']['title'],
                'year': item['target']['year'],
                'id': item['target']['id']
            })
        return jsonify(select_res)
    except Exception:
        abort(404)


# 豆瓣电影/电视详情查询
@app.route('/tv/<int:id>')
@app.route('/movie/<int:id>')
def get_movie_or_tv_detail(id):
    select_key = {'genres', 'honor_infos', 'id', 'intro', 'null_rating_reason', 'pic', 'rating', 'subject_collections',
                  'title', 'type', 'year'}
    try:
        res = miniapp_request(request.path, {})
        selected_res = {key: value for key, value in res.items() if key in select_key}
        return jsonify(selected_res)
    except Exception:
        abort(404)


# 豆瓣评分查询
@app.route('/tv/<int:id>/rating')
@app.route('/movie/<int:id>/rating')
def get_rating(id):
    select_key = {'done_count', 'stats', 'type_ranks', 'wish_count'}
    try:
        res = miniapp_request(request.path, {})
        selected_res = {key: value for key, value in res.items() if key in select_key}
        return jsonify(selected_res)
    except Exception:
        abort(404)

# 豆瓣热门短评查询
@app.route('/tv/<int:id>/hot_interests')
@app.route('/movie/<int:id>/hot_interests')
def get_hot_interests(id):
    select_key = {'comment', 'create_time', 'rating', 'vote_count'}
    try:
        res = miniapp_request(request.path, {
            'status': 'done'
        })
        selected_res = {
            'total': res['total'],
            'interests': []
        }
        for item in res['interests']:
            tmp = {key: value for key, value in item.items() if key in select_key}
            tmp.update({
                'user': {
                    'avatar': item['user']['avatar'],
                    'name': item['user']['name']
                }
            })
            selected_res['interests'].append(tmp)
        return jsonify(selected_res)
    except Exception:
        abort(404)

# 豆瓣短评查询
@app.route('/tv/<int:id>/interests')
@app.route('/movie/<int:id>/interests')
def get_interests(id):
    select_key = {'comment', 'create_time', 'rating', 'vote_count'}
    try:
        args = request.args.to_dict()
        res = miniapp_request(request.path, {
            'start': args['start'],
            'count': args['count'],
            'status': 'done',
            'order_by': 'hot'
        })
        selected_res = {
            'total': res['total'],
            'interests': []
        }
        for item in res['interests']:
            tmp = {key: value for key, value in item.items() if key in select_key}
            tmp.update({
                'user': {
                    'avatar': item['user']['avatar'],
                    'name': item['user']['name']
                }
            })
            selected_res['interests'].append(tmp)
        return jsonify(selected_res)
    except Exception:
        abort(404)


# 豆瓣影人查询
@app.route('/tv/<int:id>/celebrities')
@app.route('/movie/<int:id>/celebrities')
def get_celebrities(id):
    select_key = {'avatar', 'name'}
    try:
        res = miniapp_request(request.path, {})
        selected_res = {'actors': [], 'directors': []}
        for item in res['actors']:
            selected_res['actors'].append({key: value for key, value in item.items() if key in select_key})
        for item in res['directors']:
            selected_res['directors'].append({key: value for key, value in item.items() if key in select_key})
        return jsonify(selected_res)
    except Exception:
        abort(404)


# 豆瓣预告片查询
@app.route('/tv/<int:id>/trailers')
@app.route('/movie/<int:id>/trailers')
def get_trailers(id):
    select_key = {'cover_url', 'runtime', 'title', 'video_url'}
    try:
        res = miniapp_request(request.path, {})
        selected_res = {'trailers': []}
        for item in res['trailers']:
            selected_res['trailers'].append({key: value for key, value in item.items() if key in select_key})
        return jsonify(selected_res)
    except Exception:
        abort(404)


# 豆瓣照片查询
@app.route('/tv/<int:id>/photos')
@app.route('/movie/<int:id>/photos')
def get_photos(id):
    try:
        res = miniapp_request(request.path, {
            'start': request.args.get('start', type=int),
            'count': request.args.get('count', type=int)
        })
        selected_res = {
            'total': res['total'],
            'photos': []
        }
        for item in res['photos']:
            selected_res['photos'].append({
                'containerHeight': 320 * item['image']['small']['width'] / item['image']['small']['height'],
                'image': {
                    'large': item['image']['large']['url'],
                    'small': item['image']['small']['url']
                }
            })
        return jsonify(selected_res)
    except Exception:
        abort(404)


# 豆瓣推荐查询
@app.route('/tv/<int:id>/recommendations')
@app.route('/movie/<int:id>/recommendations')
def get_recommendations(id):
    select_key = {'null_rating_reason', 'pic', 'title', 'rating'}
    try:
        res = miniapp_request(request.path, {})
        selected_res = []
        for item in res:
            del item['pic']['large']
            selected_res.append({key: value for key, value in item.items() if key in select_key})
        return jsonify(selected_res)
    except Exception:
        abort(404)


# 豆瓣影评详情
@app.route('/tv/<int:id>/reviews')
@app.route('/movie/<int:id>/reviews')
def get_reviews(id):
    select_key = {'comments_count', 'id', 'rating', 'reshares_count', 'title', 'useful_count'}
    try:
        res = miniapp_request(request.path, {
            'start': request.args.get('start', type=int),
            'count': request.args.get('count', type=int)
        })
        selected_res = {
            'total': res['total'],
            'reviews': []
        }
        for item in res['reviews']:
            tmp = {key: value for key, value in item.items() if key in select_key}
            tmp.update({
                'abstract': item['abstract'][0:110],
                'user': {
                    'avatar': item['user']['avatar'],
                    'name': item['user']['name']
                }
            })
            selected_res['reviews'].append(tmp)
        return jsonify(selected_res)
    except Exception:
        abort(404)


# 豆瓣影评详情
@app.route('/review/<int:id>')
def get_review_detail(id):
    select_key = {'content', 'create_time', 'photos', 'rating', 'title'}
    try:
        res = miniapp_request(request.path, {})
        selected_res = {key: value for key, value in res.items() if key in select_key}
        selected_res.update({
            'user': {
                'avatar': res['user']['avatar'],
                'name': res['user']['name']
            }
        })
        return jsonify(selected_res)
    except Exception:
        abort(404)


# 豆瓣影评评论
@app.route('/review/<int:id>/comments')
def get_review_comments(id):
    try:
        res = miniapp_request(request.path, {
            'start': request.args.get('start', type=int),
            'count': request.args.get('count', type=int)
        })
        selected_res = {
            'total': res['total'],
            'comments': []
        }
        for item in res['comments']:
            selected_res['comments'].append({
                'author': {
                    'avatar': item['author']['avatar'],
                    'name': item['author']['name']
                },
                'create_time': item['create_time'],
                'text': item['text']
            })
        return jsonify(selected_res)
    except Exception:
        abort(404)


# 豆瓣热词
@app.route('/subject_collection/subject_real_time_hotest/items')
def get_real_time_hotest():
    try:
        res = miniapp_request(request.path, {
            'start': request.args.get('start', type=int),
            'count': request.args.get('count', type=int)
        })
        selected_res = []
        for item in res['subject_collection_items']:
            selected_res.append({
                'title': item['title']
            })
        return jsonify(selected_res)
    except Exception:
        abort(404)


# 豆瓣榜单详情
@app.route('/subject_collection/<id>/items')
def get_collections(id):
    try:
        subject_collection_key = {'header_bg_image', 'header_fg_image', 'id', 'name'}
        subject_collection_items_key = {'description', 'info', 'null_rating_reason', 'rating', 'title', 'year'}
        res = miniapp_request(request.path, {
            'start': request.args.get('start', type=int),
            'count': request.args.get('count', type=int)
        })
        selected_res = {
            'subject_collection': {key: value for key, value in res['subject_collection'].items() if
                                   key in subject_collection_key},
            'subject_collection_items': [],
            'total': res['total']
        }
        selected_res['subject_collection']['color'] = res['subject_collection']['background_color_scheme'][
            'primary_color_dark']
        for item in res['subject_collection_items']:
            tmp = {key: value for key, value in item.items() if key in subject_collection_items_key}
            tmp['cover'] = item['cover']['url']
            selected_res['subject_collection_items'].append(tmp)
        return jsonify(selected_res)
    except Exception:
        abort(404)


# 豆瓣榜单
@app.route('/tv/<string:rank_type>')
@app.route('/movie/<string:rank_type>')
def get_rank_list(rank_type):
    try:
        if rank_type == 'rank_list':
            res = app_request(request.path, {})['groups']
            selected_res = [{
                'selected_collections': []
            }, {
                'tabs': res[1]['tabs'],
                'title': res[1]['title']
            }, {
                'tabs': res[2]['tabs'],
                'title': res[2]['title']
            }]
            for collection in res[0]['selected_collections']:
                tmp = {key: value for key, value in collection.items() if key in {'cover_url', 'header_bg_image', 'id'}}
                tmp['items'] = []
                for item in collection['items']:
                    tmp['items'].append(
                        {key: value for key, value in item.items() if key in {'null_rating_reason', 'rating', 'title'}})
                selected_res[0]['selected_collections'].append(tmp)
        elif rank_type == 'year_ranks':
            res = app_request(request.path, request.args.to_dict())['groups'][0]['selected_collections']
            selected_res = {'selected_collections': []}
            for collection in res:
                tmp = {key: value for key, value in collection.items() if key in {'cover_url', 'header_bg_image', 'id'}}
                tmp['items'] = []
                for item in collection['items']:
                    tmp['items'].append(
                        {key: value for key, value in item.items() if key in {'null_rating_reason', 'rating', 'title'}})
                selected_res['selected_collections'].append(tmp)
        else:
            res = app_request(request.path, request.args.to_dict())['selected_collections']
            selected_res = {'selected_collections': []}
            for collection in res:
                tmp = {key: value for key, value in collection.items() if
                       key in {'cover_url', 'header_bg_image', 'id', 'medium_name', 'short_name'}}
                tmp['items'] = []
                for item in collection['items']:
                    tmp['items'].append(
                        {key: value for key, value in item.items() if key in {'null_rating_reason', 'rating', 'title'}})
                selected_res['selected_collections'].append(tmp)
        return jsonify(selected_res)
    except Exception:
        abort(404)


@app.route('/')
def root():
    abort(403)


if __name__ == '__main__':
    app.run()
