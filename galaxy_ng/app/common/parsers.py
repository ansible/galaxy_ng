import io
import logging

from rest_framework.parsers import MultiPartParser

log = logging.getLogger(__name__)


class AnsibleGalaxy29MultiPartParser(MultiPartParser):
    def parse(self, stream, media_type=None, parser_context=None):
        # Add in a crlf newline if the body is missing it between the Content-Disposition line
        # and the value

        b_data = stream.read()
        body_parts = b_data.partition(b'Content-Disposition: form-data; name="sha256"\r\n')

        new_stream = io.BytesIO()
        new_stream.write(body_parts[0])
        new_stream.write(body_parts[1])

        if not body_parts[2].startswith(b'\r\n'):
            log.warning('Malformed multipart body user-agent: %s',
                        parser_context['request'].META.get('HTTP_USER_AGENT'))

            # add the crlf to the new stream so the base parser does the right thing
            new_stream.write(b'\r\n')

        new_stream.write(body_parts[2])

        new_stream.seek(0)

        return super(AnsibleGalaxy29MultiPartParser, self).parse(new_stream,
                                                                 media_type=media_type,
                                                                 parser_context=parser_context)
