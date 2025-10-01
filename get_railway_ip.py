"""
Script to get Railway deployment IP address
Add this as a temporary route to your Flask app to see the outbound IP
"""
import requests

def get_public_ip():
    try:
        # Use multiple services in case one fails
        services = [
            'https://api.ipify.org?format=json',
            'https://ifconfig.me/ip',
            'https://icanhazip.com',
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=5)
                if 'json' in service:
                    return response.json()['ip']
                else:
                    return response.text.strip()
            except:
                continue
        return "Unable to fetch IP"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    ip = get_public_ip()
    print(f"Current outbound IP: {ip}")
