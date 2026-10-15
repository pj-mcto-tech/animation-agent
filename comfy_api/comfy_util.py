import json
import urllib.request
import urllib.parse
import websocket
import uuid

SERVER_ADDRESS = "127.0.0.1:8188"  # Or your Tailscale IP if running remotely
CLIENT_ID = str(uuid.uuid4())

def queue_prompt(workflow_json):
    p = {"prompt": workflow_json, "client_id": CLIENT_ID}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{SERVER_ADDRESS}/history/{prompt_id}") as response:
        return json.loads(response.read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{SERVER_ADDRESS}/view?{url_values}") as response:
        return response.read()

def run_workflow_headless(workflow_path, text_prompt_override=None):
    # 1. Load the API-format workflow
    with open(workflow_path, 'r') as f:
        workflow = json.load(f)
    
    # 2. Optionally patch node values programmatically (e.g., changing a CLIP text prompt or seed)
    # Note: Inspect your workflow_api.json to find the correct node ID (e.g., "6" for text)
    if text_prompt_override:
        for node_id, node_data in workflow.items():
            if node_data.get("class_type") == "CLIPTextEncode":
                node_data["inputs"]["text"] = text_prompt_override
                break # Updates the first text prompt found

    # 3. Connect to ComfyUI WebSocket to track progress
    ws = websocket.WebSocket()
    ws.connect(f"ws://{SERVER_ADDRESS}/ws?clientId={CLIENT_ID}")

    # 4. Queue the prompt
    response = queue_prompt(workflow)
    prompt_id = response['prompt_id']
    print(f"Queued workflow execution with ID: {prompt_id}")

    # 5. Monitor execution loop via WebSocket
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['prompt_id'] == prompt_id and data['node'] is None:
                    print("Execution complete!")
                    break
        # Optional: handle progress updates here

    ws.close()

    # 6. Fetch history and download generated images
    history = get_history(prompt_id)[prompt_id]
    for node_id, node_output in history['outputs'].items():
        if 'images' in node_output:
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                output_filename = f"./output_{image['filename']}"
                with open(output_filename, 'wb') as img_file:
                    img_file.write(image_data)
                print(f"Saved generated image to: {output_filename}")

if __name__ == "__main__":
    # Example usage: Run your exported workflow headlessly
    run_workflow_headless("workflow_api.json", text_prompt_override="A cinematic shot of a futuristic cyberpunk city, neon reflections, 8k")