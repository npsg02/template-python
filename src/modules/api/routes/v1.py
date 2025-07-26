"""API v1 route handlers."""

from fastapi import APIRouter, Response, File, UploadFile
import numpy as np
from fastapi.responses import StreamingResponse
from typing import Dict, List
from src.modules.transporter import add_to_queue
from src.modules.models.index import embed_text
import io
# Create v1 router
router = APIRouter(prefix='/v1', tags=['v1'])
import matplotlib.pyplot as plt
from src.modules.transporter.redis_client import pubsub
from src.modules.transporter.kafka import kafka_pubsub

@router.get("/hello")
async def hello_world():
    """Hello world endpoint."""
    add_to_queue("hello-python", "Hello from FastAPI!")
    await pubsub.publish('chat', "message")
    await kafka_pubsub.publish('chat', "messagejbdjchsjdhcjsdchbsjdch")
    return {"message": "Hello, reloaded!"}

@router.get("/health")
async def health_check(msg) -> Dict[str, str]:
    print("[chat rehealthdis] Received: message")
    """Health check endpoint."""
    return {"status": "healthy"}

@router.get("/metrics")
async def metrics() -> Dict[str, int]:
    """Application metrics endpoint."""
    return {
        "total_routes": len(router.routes),
        "api_version": 1
    }

@router.get("/plot")
async def get_plot():
    # Tạo biểu đồ
    plt.figure(figsize=(6, 4))
    x = [1, 2, 3, 4, 5]
    y = [i ** 2 for i in x]
    plt.plot(x, y, label="y = x^2")
    plt.title("Sample Plot")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.legend()

    # Lưu vào buffer
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)

    # Trả về dưới dạng ảnh PNG
    return Response(content=buf.getvalue(), media_type="image/png")

import cv2
@router.post("/edit-image/")
async def edit_image(file: UploadFile = File(...)):
    import cv2
    # Đọc file ảnh từ request
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Xử lý ảnh: ví dụ chuyển sang ảnh xám
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Chuyển lại thành ảnh màu để trả về (nếu cần)
    result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    
    # Encode ảnh thành bytes
    _, img_encoded = cv2.imencode('.jpg', result)
    return StreamingResponse(io.BytesIO(img_encoded.tobytes()), media_type="image/jpeg")


    # Load bộ phân loại khuôn mặt Haar Cascade
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

@router.post("/detect-faces/")
async def detect_faces(file: UploadFile = File(...)):
    # Đọc dữ liệu ảnh
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Chuyển sang ảnh xám để nhận diện
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Phát hiện khuôn mặt
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    
    # Vẽ hình chữ nhật quanh khuôn mặt
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
    
    # Chuyển ảnh kết quả thành bytes
    _, img_encoded = cv2.imencode('.jpg', img)
    return StreamingResponse(
        io.BytesIO(img_encoded.tobytes()), 
        media_type="image/jpeg"
    )