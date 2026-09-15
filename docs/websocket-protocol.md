# WebSocket Protocol

## Endpoint

/ws/translate

## Client -> Server

### Start Session

{
    "type": "start",
    "source_language": "en",
    "target_language": "hi"
}

### Audio

Binary WebSocket messages contain audio data.

### End Session

{
    "type": "stop"
}

## Server -> Client

### Connection

{
    "type": "connected"
}

### Transcript

{
    "type": "transcript",
    "text": "Hello"
}

### Translation

{
    "type": "translation",
    "source_text": "Hello",
    "translated_text": "नमस्ते"
}

### Audio

Binary messages contain synthesized translated audio.

### Error

{
    "type": "error",
    "code": "PROCESSING_ERROR",
    "message": "Unable to process audio"
}