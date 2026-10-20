from app.ui import build
import os
if __name__ == "__main__":
    build().launch(server_name="0.0.0.0",
                   server_port=int(os.environ.get("PORT", 7860)),
                   share=False)
