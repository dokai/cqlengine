from datetime import datetime
from uuid import uuid1

from cqlengine.exceptions import ValidationError

class QueryValue(object):
    """
    Base class for query filter values. Subclasses of these classes can
    be passed into .filter() keyword args
    """

    format_string = ':{}'

    def __init__(self, value):
        self.value = value
        self.context_id = None

    def __unicode__(self):
        return self.format_string.format(self.context_id)

    def set_context_id(self, ctx_id):
        self.context_id = ctx_id

    def get_context_size(self):
        return 1

    def update_context(self, ctx):
        ctx[str(self.context_id)] = self.value


class BaseQueryFunction(QueryValue):
    """
    Base class for filtering functions. Subclasses of these classes can
    be passed into .filter() and will be translated into CQL functions in
    the resulting query
    """

class MinTimeUUID(BaseQueryFunction):
    """
    return a fake timeuuid corresponding to the smallest possible timeuuid for the given timestamp

    http://cassandra.apache.org/doc/cql3/CQL.html#timeuuidFun
    """

    format_string = 'MinTimeUUID(:{})'

    def __init__(self, value):
        """
        :param value: the time to create a maximum time uuid from
        :type value: datetime
        """
        if not isinstance(value, datetime):
            raise ValidationError('datetime instance is required')
        super(MinTimeUUID, self).__init__(value)

    def update_context(self, ctx):
        epoch = datetime(1970, 1, 1, tzinfo=self.value.tzinfo)
        offset = epoch.tzinfo.utcoffset(epoch).total_seconds() if epoch.tzinfo else 0
        ctx[str(self.context_id)] = long(((self.value - epoch).total_seconds() - offset) * 1000)


class MaxTimeUUID(BaseQueryFunction):
    """
    return a fake timeuuid corresponding to the largest possible timeuuid for the given timestamp

    http://cassandra.apache.org/doc/cql3/CQL.html#timeuuidFun
    """

    format_string = 'MaxTimeUUID(:{})'

    def __init__(self, value):
        """
        :param value: the time to create a minimum time uuid from
        :type value: datetime
        """
        if not isinstance(value, datetime):
            raise ValidationError('datetime instance is required')
        super(MaxTimeUUID, self).__init__(value)

    def update_context(self, ctx):
        epoch = datetime(1970, 1, 1, tzinfo=self.value.tzinfo)
        offset = epoch.tzinfo.utcoffset(epoch).total_seconds() if epoch.tzinfo else 0
        ctx[str(self.context_id)] = long(((self.value - epoch).total_seconds() - offset) * 1000)


class Token(BaseQueryFunction):
    """
    compute the token for a given partition key

    http://cassandra.apache.org/doc/cql3/CQL.html#tokenFun
    """

    def __init__(self, *values):
        if len(values) == 1 and isinstance(values[0], (list, tuple)):
            values = values[0]
        super(Token, self).__init__(values)
        self._columns = None

    def set_columns(self, columns):
        self._columns = columns

    def get_context_size(self):
        return len(self.value)

    def __unicode__(self):
        token_args = ', '.join(':{}'.format(self.context_id + i) for i in range(self.get_context_size()))
        return "token({})".format(token_args)

    def update_context(self, ctx):
        for i, (col, val) in enumerate(zip(self._columns, self.value)):
            ctx[str(self.context_id + i)] = col.to_database(val)

