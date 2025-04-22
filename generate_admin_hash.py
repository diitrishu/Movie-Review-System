from werkzeug.security import generate_password_hash

# Generate hash for admin123
password = 'admin123'
hashed_password = generate_password_hash(password)
print(f"Generated hash: {hashed_password}")

# Read the SQL file
with open('database_setup.sql', 'r') as file:
    content = file.read()

# Replace the placeholder hash with the actual hash
updated_content = content.replace('YOUR_HASH_HERE', hashed_password.split('$')[2])

# Write back to the SQL file
with open('database_setup.sql', 'w') as file:
    file.write(updated_content)

print("SQL file has been updated with the correct hash!") 