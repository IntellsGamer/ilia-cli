from flask import Flask, render_template_string, request
import time

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
  <title>{{ project_name }}</title>
  <script src="https://unpkg.com/htmx.org@2"></script>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="p-8">
  <div class="max-w-md mx-auto">
    <h1 class="text-2xl font-bold">{{ project_name }}</h1>
    <p class="text-gray-600">{{ description }}</p>

    <button class="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
            hx-get="/hello"
            hx-target="#result"
            hx-swap="innerHTML">
      Say Hello
    </button>
    <div id="result" class="mt-4"></div>

    <input class="mt-4 border p-2 w-full" type="text" name="name"
           hx-post="/greet"
           hx-target="#greeting"
           hx-swap="innerHTML"
           placeholder="Type your name..." />
    <div id="greeting" class="mt-2 text-lg"></div>
  </div>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/hello')
def hello():
    time.sleep(0.3)
    return '<p class="text-green-600">Hello from HTMX + Flask!</p>'

@app.route('/greet', methods=['POST'])
def greet():
    name = request.form.get('name', 'world')
    return f'<p class="text-blue-600">Hello, {name}!</p>'

if __name__ == '__main__':
    app.run(debug=True, port=5000)
