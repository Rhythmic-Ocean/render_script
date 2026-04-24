from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="local.env")


class ENV:
    # Used for Oauth so Redirect URL is required as well
    REDIRECT_URL = os.getenv("REDIRECT_URL")
    # Seconday Osu Client ID and Client Secret.
    # Primarily used to fetch data of users with known osu id, so no redirect url required.
    # You can arbitarily put anything in osu's 'Application Callback URLs' section. I would just write 'http://localhost'
    OSU_CLIENT_ID = int(os.getenv("OSU_CLIENT_ID", "0"))
    OSU_CLIENT_SECRET = os.getenv("OSU_CLIENT_SECRET")
