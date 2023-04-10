import base64
import json
import re
import socket
import ssl

import requests
from flask import Flask, redirect, request, url_for

from Authorization import Authorization
from Socket import get_socket_connection

app = Flask(__name__)

client_id = '6445321937b340d7941a4db4f5828691'
client_secret = '84c4b2c3888a4eba8ba19d3efdbe468c'
redirect_callback = 'http://localhost:5000/callback'
auth_endpoint = 'https://todoist.com/oauth/authorize'
token_endpoint = 'https://todoist.com/oauth/access_token'
authorization = Authorization()
login = 'artenicristi03'
password = '8DRITicEXU'

proxies = {
    'https': f'http://{login}:{password}@185.253.45.117:50100'
}


def get_proxy_data(proxy):
    proxy_data = requests.get('https://ipinfo.io/json', proxies=proxy)

    data = {
        'ip': proxy_data.json()['ip'],
        'hostname': proxy_data.json()['hostname'],
        'country': proxy_data.json()['country'],
        'region': proxy_data.json()['region']
    }

    return data


def get_response_data(sock):
    response_data = sock.recv(1024).decode('utf-8')
    response_headers, response_body = response_data.split("\r\n\r\n", 1)
    content_length_match = re.search(r'content-length:\s*(\d+)', response_headers.lower())
    content_length = int(content_length_match.group(1))

    while len(response_body) < content_length:
        response_body += sock.recv(1024).decode('utf-8')

    return response_body


@app.route('/')
def main():
    return {'type': authorization.type, 'token': authorization.token}


@app.route('/get-grant-code')
def get_code():
    scopes = 'data:read_write,data:delete'

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

    print(get_proxy_data(proxies))

    response = requests.get(url, headers=headers, proxies=proxies)

    return response.json()


@app.route('/tasks/new')
def add_task():
    url = 'https://api.todoist.com/rest/v2/tasks'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'{authorization.type} {authorization.token}',
    }

    task_data = {
        'content': 'from routes /tasks/new',
        'due_string': 'tomorrow at 12:20',
        'due_lang': 'en',
        'priority': 4
    }

    response = requests.post(url, json=task_data, headers=headers, proxies=proxies)

    return response.json()


@app.route('/test')
def test():
    host = 'api.todoist.com'
    port = 443

    sock = get_socket_connection(host, port)

    context = ssl.create_default_context()
    sock = context.wrap_socket(sock, server_hostname=host)

    request_headers = (
        'GET /rest/v2/tasks HTTP/1.0\r\n'
        f'Host: {host}\r\n'
        f'Authorization: {authorization.type} {authorization.token}\r\n\r\n'
    )

    sock.sendall(request_headers.encode())

    response_body = get_response_data(sock)
    sock.close()

    return response_body


@app.route('/test/post')
def test_post():
    host = 'api.todoist.com'
    port = 443

    sock = get_socket_connection(host, port)
    context = ssl.create_default_context()
    sock = context.wrap_socket(sock, server_hostname=host)

    task_data = {
        'content': 'from python',
        'due_string': 'today at 12:20',
        'due_lang': 'en',
        'priority': 1
    }
    request_body = json.dumps(task_data)

    request_headers = (
        'POST /rest/v2/tasks HTTP/1.1\r\n'
        f'Host: {host}\r\n'
        'Content-Type: application/json\r\n'
        f'Authorization: {authorization.type} {authorization.token}\r\n'
        f'Content-Length: {len(request_body)}\r\n\r\n'
    )

    request_data = request_headers.encode('utf-8') + request_body.encode('utf-8')
    sock.sendall(request_data)

    response_body = get_response_data(sock)
    sock.close()

    return response_body


@app.route('/test/proxy')
def test_proxy():
    proxy_host = '185.253.45.117'
    proxy_port = 50100

    external_host = 'api.todoist.com'
    external_port = 443

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((proxy_host, proxy_port))

    # context = ssl.create_default_context()
    # sock = context.wrap_socket(sock, server_hostname=proxy_host)

    auth = f'{login}:{password}'.encode('utf-8')
    connect_request = f'CONNECT {external_host}:{external_port} HTTP/1.1\r\n' \
                      f'Host: {external_host}:{external_port}\r\n' \
                      f'Proxy-Authorization: Basic {base64.b64encode(auth)}\r\n' \
                      'Proxy-Connection: keep-alive\r\n\r\n'

    sock.send(connect_request.encode())

    response = sock.recv(4096)

    print(response)

    return 'after'

    # auth = f"{login}:{password}".encode()
    # sock.sendall(f"Proxy-Authorization: Basic {base64.b64encode(auth)}\r\n".encode())

    context = ssl.create_default_context()
    sock = context.wrap_socket(sock, server_hostname=external_host)

    http_request = f"GET /rest/v2/tasks HTTP/1.0\r\nHost: {external_host}\r\n\r\n"
    sock.send(http_request.encode())

    response = sock.recv(4096).decode()
    print(response)

    sock.close()

    return response
