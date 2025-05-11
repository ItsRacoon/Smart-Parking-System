# Smart Parking System

A comprehensive parking management system with computer vision integration for real-time space detection, user management, booking, and payment processing.

## Features

- **Real-time Parking Space Detection**: Uses computer vision to detect available parking spaces
- **User Authentication System**: Register, login, and manage user profiles
- **Vehicle Management**: Add and manage multiple vehicles per user
- **Booking System**: Book parking spaces with flexible duration options
- **Payment Processing**: Secure payment integration with multiple payment methods
- **Zone-based Pricing**: Different rates for different parking zones (General, Premium, VIP, Disabled)
- **Admin Dashboard**: Comprehensive admin interface with statistics and management tools
- **Reporting System**: Generate and export detailed reports
- **Mobile-Friendly Design**: Responsive interface that works on all devices

## Technology Stack

- **Backend**: Python with Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Computer Vision**: OpenCV for real-time space detection
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Authentication**: Custom authentication system with session management
- **Payment Processing**: Simulated payment gateway (can be integrated with real payment processors)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/smart-parking-system.git
   cd smart-parking-system
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```
   python app.py
   ```

5. Run the application:
   ```
   python app.py
   ```

6. Access the application at `http://localhost:5000`

## Usage

### User Features

1. **Registration and Login**:
   - Create a new account or login with existing credentials
   - Manage your profile and vehicles

2. **Booking a Space**:
   - View available spaces in real-time
   - Select a space, duration, and vehicle
   - Complete payment to confirm booking

3. **Managing Bookings**:
   - View all your active bookings
   - Cancel bookings if needed
   - Access booking details and QR codes for entry

### Admin Features

1. **Dashboard**:
   - View key statistics and metrics
   - Monitor parking space utilization

2. **Space Management**:
   - Define and configure parking spaces
   - Set rates for different zones

3. **User Management**:
   - View and manage user accounts
   - Access user booking history

4. **Booking Management**:
   - View all bookings in the system
   - Filter and search bookings
   - Cancel or modify bookings

5. **Reporting**:
   - Generate revenue reports
   - Export data to CSV

## Project Structure

```
smart-parking-system/
├── app.py                 # Main application file
├── auth.py                # Authentication module
├── payment.py             # Payment processing module
├── models.py              # Database models
├── parkingspacepicker.py  # Tool for defining parking spaces
├── static/                # Static files (CSS, JS, images)
├── templates/             # HTML templates
│   ├── admin/             # Admin interface templates
│   ├── auth/              # Authentication templates
│   ├── errors/            # Error pages
│   ├── payment/           # Payment templates
│   └── layout.html        # Base template
├── CarParkPos             # Parking space positions data
├── carPark.mp4            # Sample video for space detection
├── carParkImg.png         # Reference image for space picker
└── requirements.txt       # Project dependencies
```

## Configuration

The application can be configured by modifying the following settings in `app.py`:

- `SECRET_KEY`: Secret key for session security
- `SQLALCHEMY_DATABASE_URI`: Database connection string
- `UPLOAD_FOLDER`: Path for file uploads
- `MAX_CONTENT_LENGTH`: Maximum upload file size

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenCV for computer vision capabilities
- Flask for the web framework
- Bootstrap for the frontend design
- All contributors who have helped improve this project