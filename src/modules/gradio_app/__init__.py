import gradio as gr

def greet(name):
    return f"Hello {name}!"

def detection(image, conf_threshold):
    # Placeholder for YOLOv10 detection logic
    # This function should process the image and return the modified image
    # For now, we will just return the original image
    return image

with gr.Blocks() as block:
    gr.Markdown("# 🚀 Gradio Hello World")

    gr.HTML(
        """
        <h1 style='text-align: center'>
        YOLOv10 Webcam Stream (Powered by WebRTC ⚡️)
        </h1>
        """
    )
    
    with gr.Row():
        name_input = gr.Textbox(label="Your Name", placeholder="Enter your name...")
        output = gr.Textbox(label="Greeting")


    greet_btn = gr.Button("Greet")
    greet_btn.click(fn=greet, inputs=name_input, outputs=output)
    
    gr.Examples(
        examples=["Alice", "Bob", "Charlie"],
        inputs=name_input
    )
    

block.launch(server_port=7860, server_name="0.0.0.0")

print("Gradio app is running on http://localhost:7860")