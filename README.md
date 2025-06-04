# News Management System

A luxurious and bold news management system built with Flask, Python, and MySQL.

## Features

- User authentication and role-based access control
- Article management with rich text editing
- Category management
- Responsive, luxurious design with smooth animations
- Admin dashboard for content management
- Search functionality
- Mobile-friendly interface

## Prerequisites

- Python 3.8+
- MySQL 5.7+
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd news_system
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with the following content:
```
# Flask settings
SECRET_KEY=your_secret_key_here
FLASK_APP=app.py
FLASK_ENV=development

# Database settings
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=news_system
```

5. Initialize the database:
```bash
python database/init_db.py
```

6. Run the application:
```bash
flask run
```

7. Access the application at http://localhost:5000

## Default Admin User

- Email: admin@news.com
- Password: admin123

## Project Structure

```
news_system/
├── static/
│   ├── css/         # Stylesheets
│   ├── js/          # JavaScript files
│   └── images/      # Images and uploads
├── templates/       # HTML templates
├── database/        # Database scripts
├── app.py           # Main application file
├── requirements.txt # Python dependencies
└── README.md        # This file
```

## Design

The design follows a luxurious and bold aesthetic with:
- Clean typography using premium fonts
- Sophisticated color palette
- Ample white space
- Smooth animations and transitions
- Sticky header with logo
- Mobile-responsive layout

## License

This project is licensed under the MIT License. 

## Additional Notes

To set the admin password to "admin123", run this command in your terminal:

```
flask create-admin admin admin@example.com admin123
```

This will create an admin user with:
- Username: admin
- Email: admin@example.com
- Password: admin123
- Role: admin

After running this command, you can log in at `/login` with:
- Email: admin@example.com
- Password: admin123

Then you'll have full admin access to the system. 
