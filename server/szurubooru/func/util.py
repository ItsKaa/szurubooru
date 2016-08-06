import os
import datetime
import hashlib
import re
import tempfile
from contextlib import contextmanager
from szurubooru import errors

def snake_case_to_lower_camel_case(text):
    components = text.split('_')
    return components[0] + ''.join(word[0].upper() + word[1:] for word in components[1:])

def snake_case_to_lower_camel_case_keys(source):
    target = {}
    for key, value in source.items():
        target[snake_case_to_lower_camel_case(key)] = value
    return target

def get_serialization_options(ctx):
    return ctx.get_param_as_list('fields', required=False, default=None)

def serialize_entity(entity, field_factories, options):
    if not entity:
        return None
    if not options:
        options = field_factories.keys()
    ret = {}
    for key in options:
        try:
            factory = field_factories[key]
            ret[key] = factory()
        except KeyError:
            raise errors.ValidationError('Invalid key: %r. Valid keys: %r.' % (
                key, list(sorted(field_factories.keys()))))
    return ret

@contextmanager
def create_temp_file(**kwargs):
    (handle, path) = tempfile.mkstemp(**kwargs)
    os.close(handle)
    try:
        with open(path, 'r+b') as handle:
            yield handle
    finally:
        os.remove(path)

def unalias_dict(input_dict):
    output_dict = {}
    for key_list, value in input_dict.items():
        if isinstance(key_list, str):
            key_list = [key_list]
        for key in key_list:
            output_dict[key] = value
    return output_dict

def get_md5(source):
    if not isinstance(source, bytes):
        source = source.encode('utf-8')
    md5 = hashlib.md5()
    md5.update(source)
    return md5.hexdigest()

def flip(source):
    return {v: k for k, v in source.items()}

def is_valid_email(email):
    ''' Return whether given email address is valid or empty. '''
    return not email or re.match(r'^[^@]*@[^@]*\.[^@]*$', email)

class dotdict(dict): # pylint: disable=invalid-name
    ''' dot.notation access to dictionary attributes. '''
    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def parse_time_range(value):
    ''' Return tuple containing min/max time for given text representation. '''
    one_day = datetime.timedelta(days=1)
    one_second = datetime.timedelta(seconds=1)

    value = value.lower()
    if not value:
        raise errors.ValidationError('Empty date format.')

    if value == 'today':
        now = datetime.datetime.utcnow()
        return (
            datetime.datetime(now.year, now.month, now.day, 0, 0, 0),
            datetime.datetime(now.year, now.month, now.day, 0, 0, 0) \
                + one_day - one_second)

    if value == 'yesterday':
        now = datetime.datetime.utcnow()
        return (
            datetime.datetime(now.year, now.month, now.day, 0, 0, 0) - one_day,
            datetime.datetime(now.year, now.month, now.day, 0, 0, 0) \
                - one_second)

    match = re.match(r'^(\d{4})$', value)
    if match:
        year = int(match.group(1))
        return (
            datetime.datetime(year, 1, 1),
            datetime.datetime(year + 1, 1, 1) - one_second)

    match = re.match(r'^(\d{4})-(\d{1,2})$', value)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        return (
            datetime.datetime(year, month, 1),
            datetime.datetime(year, month + 1, 1) - one_second)

    match = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', value)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return (
            datetime.datetime(year, month, day),
            datetime.datetime(year, month, day + 1) - one_second)

    raise errors.ValidationError('Invalid date format: %r.' % value)

def icase_unique(source):
    target = []
    target_low = []
    for source_item in source:
        if source_item.lower() not in target_low:
            target.append(source_item)
            target_low.append(source_item.lower())
    return target

def value_exceeds_column_size(value, column):
    if not value:
        return False
    max_length = column.property.columns[0].type.length
    if max_length is None:
        return False
    return len(value) > max_length

def verify_version(entity, context, field_name='version'):
    actual_version = context.get_param_as_int(field_name, required=True)
    expected_version = entity.version
    if actual_version != expected_version:
        raise errors.InvalidParameterError(
            'Someone else modified this in the meantime. ' +
            'Please try again.')

def bump_version(entity):
    entity.version += 1
