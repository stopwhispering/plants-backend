from flask import request


def parse_resource_from_request(req: request):
    items = req.url.split('/')
    index_start = items.index('backend') + 1
    resource_name = '/'.join(items[index_start:])
    if '?' in resource_name:
        resource_name = resource_name[:resource_name.find('?')]

    return resource_name
