#!
# -*- coding: utf_8 -*-

from com.sun.star.sdbc import SQLException

from unolib import KeyMap
from unolib import getResourceLocation
from unolib import getSimpleFile

from .dbconfig import g_path
from .dbqueries import getSqlQuery
from .dbtools import getTablesAndStatements
from .dbtools import getDataSourceCall
from .dbtools import getSequenceFromResult
from .dbtools import getDataFromResult
from .dbtools import getKeyMapFromResult
from .dbtools import registerDataSource
from .dbtools import executeQueries
from .dbtools import executeSqlQueries
from .dbtools import getDataSourceConnection
from .dbtools import createDataSource
from .dbtools import checkDataBase
from .dbtools import createStaticTable

import traceback


def getDataSourceUrl(ctx, dbname, plugin, register):
    error = None
    url = getResourceLocation(ctx, plugin, g_path)
    odb = '%s/%s.odb' % (url, dbname)
    if not getSimpleFile(ctx).exists(odb):
        dbcontext = ctx.ServiceManager.createInstance('com.sun.star.sdb.DatabaseContext')
        datasource = createDataSource(dbcontext, url, dbname)
        error = _createDataBase(ctx, datasource, url, dbname)
        if error is None:
            datasource.DatabaseDocument.storeAsURL(odb, ())
            if register:
                registerDataSource(dbcontext, dbname, odb)
    return url, error

def _createDataBase(ctx, datasource, url, dbname):
    error = None
    try:
        connection = datasource.getConnection('', '')
    except SQLException as e:
        error = e
    else:
        version, error = checkDataBase(ctx, connection)
        if error is None:
            statement = connection.createStatement()
            createStaticTable(statement, _getStaticTables())
            tables, statements = getTablesAndStatements(statement, version)
            executeSqlQueries(statement, tables)
            _createPreparedStatement(ctx, datasource, statements)
            executeQueries(statement, _getQueries())
            _createDynamicView(statement)
        connection.close()
        connection.dispose()
    return error

def _getTableColumns(connection, tables):
    columns = {}
    metadata = connection.MetaData
    for table in tables:
        columns[table] = _getColumns(metadata, table)
    return columns

def _getColumns(metadata, table):
    columns = []
    result = metadata.getColumns("", "", table, "%")
    while result.next():
        column = '"%s"' % result.getString(4)
        columns.append(column)
    return columns

def _createPreparedStatement(ctx, datasource, statements):
    queries = datasource.getQueryDefinitions()
    for name, sql in statements.items():
        if not queries.hasByName(name):
            query = ctx.ServiceManager.createInstance("com.sun.star.sdb.QueryDefinition")
            query.Command = sql
            queries.insertByName(name, query)

def _createDynamicView(statement):
    views, triggers = _getViewsAndTriggers(statement)
    executeSqlQueries(statement, views)
    executeSqlQueries(statement, triggers)

def _getViewsAndTriggers(statement):
    c1 = []
    s1 = []
    f1 = []
    queries = []
    triggers = []
    triggercore = []
    call = getDataSourceCall(statement.getConnection(), 'getViews')
    tables = getSequenceFromResult(statement.executeQuery(getSqlQuery('getViewName')))
    for table in tables:
        call.setString(1, table)
        result = call.executeQuery()
        while result.next():
            c2 = []
            s2 = []
            f2 = []
            trigger = {}
            data = getDataFromResult(result)
            view = data['View']
            ptable = data['PrimaryTable']
            pcolumn = data['PrimaryColumn']
            ftable = data['ForeignTable']
            fcolumn = data['ForeignColumn']
            labelid = data['LabelId']
            typeid = data['TypeId']
            c1.append('"%s"' % view)
            c2.append('"%s"' % pcolumn)
            c2.append('"Value"')
            s1.append('"%s"."Value"' % view)
            s2.append('"%s"."%s"' % (table, pcolumn))
            s2.append('"%s"."Value"' % table)
            f = 'LEFT JOIN "%s" ON "%s"."%s"="%s"."%s"' % (view, ftable, fcolumn, view, pcolumn)
            f1.append(f)
            f2.append('"%s"' % table)
            f = 'JOIN "Labels" ON "%s"."Label"="Labels"."Label" AND "Labels"."Label"=%s'
            f2.append(f % (table, labelid))
            if typeid is not None:
                f = 'JOIN "Types" ON "%s"."Type"="Types"."Type" AND "Types"."Type"=%s'
                f2.append(f % (table, typeid))
            format = (view, ','.join(c2), ','.join(s2), ' '.join(f2))
            query = getSqlQuery('createView', format)
            queries.append(query)
            triggercore.append(getSqlQuery('createTriggerUpdateAddressBookCore', data))
    call.close()
    if queries:
        c1.insert(0, '"%s"' % pcolumn)
        s1.insert(0, '"%s"."%s"' % (ftable, fcolumn))
        f1.insert(0, 'ON "%s"."%s"="%s"."%s"' % (ptable, pcolumn, ftable, pcolumn))
        f1.insert(0, '"%s" JOIN "%s"' % (ptable, ftable))
        f1.append('WHERE "%s"."Resource" = CURRENT_USER' % ptable)
        format = ('AddressBook', ','.join(c1), ','.join(s1), ' '.join(f1))
        query = getSqlQuery('createView', format)
        queries.append(query)
        queries.append( getSqlQuery('grantRole'))
        trigger = getSqlQuery('createTriggerUpdateAddressBook', ' '.join(triggercore))
        triggers.append(trigger)
    return queries, triggers

def _getStaticTables():
    tables = ('Tables',
              'Types',
              'Columns',
              'TableType',
              'TableColumn',
              'Fields',
              'Labels',
              'TableLabel',
              'Settings')
    return tables

def _getQueries():
    return ('createRole', )
