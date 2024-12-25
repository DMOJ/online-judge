import json
import base64
import requests
from .settings import (MARTOR_IMGUR_CLIENT_ID, MARTOR_IMGUR_API_KEY)

requests.packages.urllib3.disable_warnings()


def imgur_uploader(image):
    """
    Basic imgur uploader return as json data.
    :param `image` is from `request.FILES['markdown-image-upload']`

    Return:
        success: {'status': 200, 'link': <link_image>, 'name': <image_name>}
        error  : {'status': <error_code>, 'erorr': <erorr_message>}
    """
    url_api = 'https://api.imgur.com/3/upload.json'
    headers = {'Authorization': 'Client-ID ' + MARTOR_IMGUR_CLIENT_ID}
    response = requests.post(
        url_api,
        headers=headers,
        data={
            'key': MARTOR_IMGUR_API_KEY,
            'image': base64.b64encode(image.read()),
            'type': 'base64',
            'name': image.name
        }
    )

    """
    Some function we got from `response`:

    ['connection', 'content', 'cookies', 'elapsed', 'encoding', 'headers','history',
    'is_permanent_redirect', 'is_redirect', 'iter_content', 'iter_lines', 'json',
    'links', 'ok', 'raise_for_status', 'raw', 'reason', 'request', 'status_code', 'text', 'url']
    """
    if response.status_code == 200:
        respdata = json.loads(response.content.decode('utf-8'))
        return json.dumps({
            'status': respdata['status'],
            'link': respdata['data']['link'],
            'name': respdata['data']['name']
        })
    elif response.status_code == 415:
        # Unsupport File type
        return json.dumps({
            'status': response.status_code,
            'error': response.reason
        })
    return json.dumps({
        'status': response.status_code,
        'error': response.content.decode('utf-8')
    })
