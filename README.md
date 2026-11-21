# The Journal — Blog Application (Flask + SQLite)

## Features
- Register, log in, log out
- Create, read, edit and delete your own posts
- Only the author can edit or delete a post
- SQLite database created automatically

## Setup (step by step)

1. Install Python 3.10 or newer.
2. Open a terminal inside the `blog-app` folder.
3. (Optional but recommended) create a virtual environment:
   - Windows: `python -m venv venv` then `venv\Scripts\activate`
   - Mac/Linux: `python3 -m venv venv` then `source venv/bin/activate`
4. Install the dependency:
   `pip install -r requirements.txt`
5. Start the app:
   `python app.py`
6. Open your browser at `http://127.0.0.1:5000`

The file `blog.db` is created automatically the first time you run the app.

## Using the app
1. Click **Sign up**, choose a username (3+ characters) and password (6+ characters).
2. Click **Log in**.
3. Click **Write** to publish a post. Separate paragraphs with a blank line.
4. Open any post you wrote to see **Edit** and **Delete**.

## Before deploying
- Set a strong secret key: `SECRET_KEY=your-long-random-string`
- Turn off debug mode in `app.py` (`app.run(debug=False)`) for production.
