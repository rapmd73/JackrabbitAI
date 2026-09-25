#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Strict CGI helper class for safe GET and POST form endpoints.
# POST data is never logged, stored, echoed, or placed in errors by this class.

import html
import json
import os
import sys
from urllib.parse import parse_qsl


class CGIError(ValueError):
    # Controlled CGI error that never contains request contents.
    pass


class CGI:
    # Create one parser for one CGI request.
    def __init__(self, environ=None, stream=None, max_bytes=1024 * 1024,
                 max_args=1024, strict_utf8=True, trim=False):
        self.environ = os.environ if environ is None else environ
        self.stream = stream if stream is not None else getattr(sys.stdin, "buffer", sys.stdin)
        self.max_bytes = max_bytes
        self.max_args = max_args
        self.strict_utf8 = strict_utf8
        self.trim = trim

    # Return the normalized request method.
    def Method(self):
        return self.environ.get("REQUEST_METHOD", "").upper()

    # Read exactly the declared number of bytes.
    def ReadExact(self, length):
        raw = self.stream.read(length)
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if len(raw) != length:
            raise CGIError("request body length does not match CONTENT_LENGTH")
        return raw

    # Read a bounded POST body without logging or echoing it.
    def ReadRequestBody(self, require_post=False, require_length=False):
        if self.max_bytes < 0:
            raise ValueError("max_bytes must not be negative")
        if require_post and self.Method() != "POST":
            raise CGIError("POST required")

        raw_length = self.environ.get("CONTENT_LENGTH", "")
        if raw_length == "":
            if require_length:
                raise CGIError("CONTENT_LENGTH required")
            raw = self.stream.read(self.max_bytes + 1)
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
            if len(raw) > self.max_bytes:
                raise CGIError("request body exceeds the configured limit")
        else:
            try:
                length = int(raw_length)
            except (TypeError, ValueError) as error:
                raise CGIError("CONTENT_LENGTH must be an integer") from error
            if length < 0:
                raise CGIError("CONTENT_LENGTH cannot be negative")
            if length > self.max_bytes:
                raise CGIError("request body exceeds the configured limit")
            raw = self.ReadExact(length)

        try:
            return raw.decode("utf-8", errors="strict" if self.strict_utf8 else "replace")
        except UnicodeDecodeError as error:
            raise CGIError("request body is not valid UTF-8") from error

    # Parse URL-encoded name/value pairs.
    def Pairs(self, data):
        try:
            pairs = parse_qsl(
                data,
                keep_blank_values=True,
                strict_parsing=False,
                encoding="utf-8",
                errors="strict" if self.strict_utf8 else "replace",
                max_num_fields=self.max_args,
            )
        except (UnicodeDecodeError, ValueError) as error:
            raise CGIError("invalid URL-encoded request data") from error
        if self.trim:
            return [(name.strip(), value.strip()) for name, value in pairs]
        return pairs

    # Convert pairs to a map while preserving duplicate fields.
    def FieldMap(self, pairs):
        fields = {}
        for name, value in pairs:
            fields.setdefault(name, []).append(value)
        return fields

    # Parse GET query data only; never reads stdin.
    def ParseQuery(self, query=None):
        if self.Method() != "GET":
            raise CGIError("GET required")
        if query is None:
            query = self.environ.get("QUERY_STRING", "")
        return self.FieldMap(self.Pairs(query))

    # Strictly parse an application/x-www-form-urlencoded POST.
    def ParsePOST(self):
        if self.Method() != "POST":
            raise CGIError("POST required")
        content_type = self.environ.get("CONTENT_TYPE", "")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/x-www-form-urlencoded":
            raise CGIError("application/x-www-form-urlencoded required")
        body = self.ReadRequestBody(require_post=True, require_length=True)
        return self.FieldMap(self.Pairs(body))

    # Accept exactly GET or POST and reject every other method.
    def ParseRequest(self):
        method = self.Method()
        if method == "GET":
            return self.ParseQuery()
        if method == "POST":
            return self.ParsePOST()
        raise CGIError("GET or POST required")

    # Read one field or all values for a field.
    def ReadField(self, name, fields=None, default="", first=True):
        if fields is None:
            fields = self.ParseRequest()
        values = fields.get(name, [])
        if not values:
            return default
        return values[0] if first else values

    # Escape text for safe HTML output.
    @staticmethod
    def EscapeHTML(value, quote=True):
        return html.escape(str(value), quote=quote)

    # Read a UTF-8 template file.
    @staticmethod
    def ReadTemplate(path, encoding="utf-8"):
        with open(path, "r", encoding=encoding) as handle:
            return handle.read().strip()

    # Replace one required template marker.
    @staticmethod
    def RenderTemplate(template, marker, replacement):
        if template is None:
            raise CGIError("template is unavailable")
        if marker not in template:
            raise CGIError("template marker is unavailable")
        return template.replace(marker, str(replacement), 1)

    # Emit the CGI response header before the body.
    @staticmethod
    def WriteHeader(content_type="text/html", charset="utf-8", status=None):
        if status is not None:
            sys.stdout.write(f"Status: {status}\r\n")
        if charset:
            content_type = f"{content_type}; charset={charset}"
        sys.stdout.write(f"Content-Type: {content_type}\r\n\r\n")

    # Emit a response body.
    @classmethod
    def Respond(cls, body, content_type="text/html", charset="utf-8", status=None):
        cls.WriteHeader(content_type, charset, status)
        sys.stdout.write(str(body))

    # Emit a JSON response.
    @classmethod
    def RespondJSON(cls, value, status=None):
        cls.Respond(json.dumps(value, ensure_ascii=False, indent=2),
                    "application/json", "utf-8", status)

    # Emit an escaped HTML error response.
    @classmethod
    def RespondError(cls, message, status="400 Bad Request"):
        body = "<!doctype html><html><body><h1>{}</h1></body></html>".format(
            cls.EscapeHTML(message)
        )
        cls.Respond(body, status=status)
