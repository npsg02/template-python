import uvicorn 
from .app import app as api_app

def main():
    """Main application entry point."""
    try:
        print("Start api...")
        uvicorn.run(
            api_app,
            host="0.0.0.0",
            port=8800,
            reload=False,
        )
    except Exception as e:
        print(f"Application failed to start: {e}", exc_info=True)
        raise
main()