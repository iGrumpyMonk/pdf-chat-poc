from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from auth import Base, User, get_password_hash
import getpass

# Database URL (same as your main app)
DATABASE_URL = "sqlite:///./auth.db"


def create_first_admin():
    """Create the first admin user interactively"""

    print("🔐 Creating First Admin User")
    print("=" * 40)

    # Connect to database
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Make sure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Check if any admin already exists
        existing_admin = db.query(User).filter(User.role == "admin").first()
        if existing_admin:
            print(f"⚠️  Admin already exists: {existing_admin.email}")
            response = input("Create another admin? (y/N): ").lower()
            if response != 'y':
                print("Exiting...")
                return

        # Get admin details from user
        print("\nEnter admin details:")
        email = input("📧 Email: ").strip()

        if not email:
            print("❌ Email is required!")
            return

        # Check if email already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"❌ User with email {email} already exists!")
            return

        full_name = input("👤 Full Name (optional): ").strip()
        username = input("🏷️  Username (optional): ").strip()

        # Get password securely
        while True:
            password = getpass.getpass("🔑 Password: ")
            if len(password) < 6:
                print("❌ Password must be at least 6 characters!")
                continue

            password_confirm = getpass.getpass("🔑 Confirm Password: ")
            if password != password_confirm:
                print("❌ Passwords don't match!")
                continue
            break

        # Create admin user
        admin_user = User(
            email=email,
            username=username if username else None,
            full_name=full_name if full_name else None,
            hashed_password=get_password_hash(password),
            role="admin",
            is_active=True,
            is_verified=True
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("\n✅ Admin user created successfully!")
        print(f"📧 Email: {admin_user.email}")
        print(f"👤 Name: {admin_user.full_name or 'Not provided'}")
        print(f"👑 Role: {admin_user.role}")
        print(f"🆔 ID: {admin_user.id}")
        print("\n🚀 You can now login with these credentials!")

    except Exception as e:
        print(f"❌ Error creating admin: {e}")
        db.rollback()
    finally:
        db.close()


def create_test_users():
    """Create some test users for testing"""

    print("\n🧪 Creating Test Users")
    print("=" * 30)

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    test_users = [
        {
            "email": "user@test.com",
            "password": "password123",
            "full_name": "Test User",
            "role": "user"
        },
        {
            "email": "manager@test.com",
            "password": "password123",
            "full_name": "Test Manager",
            "role": "manager"
        }
    ]

    try:
        for user_data in test_users:
            # Check if user already exists
            existing = db.query(User).filter(
                User.email == user_data["email"]).first()
            if existing:
                print(f"⚠️  {user_data['email']} already exists, skipping...")
                continue

            user = User(
                email=user_data["email"],
                full_name=user_data["full_name"],
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"],
                is_active=True,
                is_verified=True
            )

            db.add(user)
            db.commit()
            print(f"✅ Created {user_data['role']}: {user_data['email']}")

        print("\n🎯 Test users created! Passwords are all 'password123'")

    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        db.rollback()
    finally:
        db.close()


def show_all_users():
    """Show all users in the database"""

    print("\n👥 All Users in Database")
    print("=" * 40)

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        users = db.query(User).all()

        if not users:
            print("No users found in database.")
            return

        for user in users:
            role_emoji = {"admin": "👑", "manager": "👔",
                          "user": "👤"}.get(user.role, "❓")
            status = "✅" if user.is_active else "❌"

            print(f"{role_emoji} {user.email}")
            print(f"   Name: {user.full_name or 'Not set'}")
            print(f"   Role: {user.role}")
            print(f"   Active: {status}")
            print(f"   ID: {user.id}")
            print()

    except Exception as e:
        print(f"❌ Error fetching users: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("🔐 Admin User Management")
    print("=" * 50)

    while True:
        print("\nWhat would you like to do?")
        print("1. Create admin user")
        print("2. Create test users (user@test.com, manager@test.com)")
        print("3. Show all users")
        print("4. Exit")

        choice = input("\nChoice (1-4): ").strip()

        if choice == "1":
            create_first_admin()
        elif choice == "2":
            create_test_users()
        elif choice == "3":
            show_all_users()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice!")
