from flask import request


def parse_resource_from_request(req: request):
    items = req.url.split('/')
    index_start = items.index('backend') + 1
    return '/'.join(items[index_start:])
