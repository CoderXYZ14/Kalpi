from rest_framework.response import Response


def success_response(data, status=200):
    return Response({"success": True, "data": data}, status=status)


def error_response(message, status=400, details=None):
    body = {"success": False, "error": message}
    if details:
        body["details"] = details
    return Response(body, status=status)
