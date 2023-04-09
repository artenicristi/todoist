import ssl
import sys
import traceback
import socket

from flask import Flask, redirect, request, url_for
from todoist_api_python.api import TodoistAPI
from Authorization import Authorization
import requests

app = Flask(__name__)

client_id = '6445321937b340d7941a4db4f5828691'
client_secret = '84c4b2c3888a4eba8ba19d3efdbe468c'
redirect_callback = 'http://localhost:5000/callback'
auth_endpoint = 'https://todoist.com/oauth/authorize'
token_endpoint = 'https://todoist.com/oauth/access_token'
authorization = Authorization()


@app.route('/')
def main():
    return {'type': authorization.type, 'token': authorization.token}


@app.route('/get-grant-code')
def get_code():
    scopes = 'data:read_write,data:delete,project:delete'

    url = f'{auth_endpoint}?' \
          f'scope={scopes}&' \
          'response_type=code&' \
          f'redirect_uri={redirect_callback}&' \
          f'client_id={client_id}&' \
          'state=test_state&' \
          'include_granted_scopes=true&' \
          'approval_prompt=force'

    return redirect(url)


@app.route('/callback')
def callback():
    authorization_code = request.args['code']

    post_data = {
        'code': authorization_code,
        'client_id': client_id,
        'client_secret': client_secret,
    }

    response = requests.post(token_endpoint, data=post_data)

    authorization.type = response.json()['token_type']
    authorization.token = response.json()['access_token']

    return redirect(url_for('main'))


@app.route('/tasks')
def get_tasks():
    url = 'https://api.todoist.com/rest/v2/tasks'

    headers = {
        'Authorization': f'{authorization.type} {authorization.token}'
    }

    response = requests.get(url, headers=headers)

    return response.json()


@app.route('/tasks/new')
def add_task():
    # api = TodoistAPI(authorization.token)
    #
    # try:
    #     task = api.add_task(
    #         content="Buy Milk",
    #         due_string="tomorrow at 12:00",
    #         due_lang="en",
    #         priority=4,
    #     )
    #     print(task)
    # except Exception as error:
    #     print(error)

    url = 'https://api.todoist.com/rest/v2/tasks'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'{authorization.type} {authorization.token}',
    }

    task_data = {
        'content': 'Buy Milk',
        'due_string': 'tomorrow at 12:20',
        'due_lang': 'en',
        'priority': 4
    }

    post_data = {
        'content': task_data,
    }

    response = requests.post(url, data={'content': 'from python'}, headers=headers)
    print(response)

    return 'added task'


@app.route('/test')
def test():
    host = 'api.todoist.com'
    port = 443

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (host, port)
    sock.connect(server_address)

    if port == 443:
        context = ssl.create_default_context()
        sock = context.wrap_socket(sock, server_hostname=host)

    request_headers = 'GET /rest/v2/tasks HTTP/1.0\r\nHOST: {}' \
                      f'\r\nAuthorization: {authorization.type} {authorization.token}' \
                      '\r\nSave-Data: on\r\n\r\n'.format(host)

    sock.sendall(request_headers.encode())

    response = b''
    while True:
        data = sock.recv(2048)
        if not data:
            break
        response += data

    sock.close()

    return response
