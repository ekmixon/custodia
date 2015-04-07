# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

from __future__ import print_function
from custodia.store.interface import CSStore, CSStoreError
import os
import sqlite3
import sys


def log_error(error):
    print(error, file=sys.stderr)


class SqliteStore(CSStore):

    def __init__(self, config):
        if 'dburi' not in config:
            raise ValueError('Missing "dburi" for Sqlite Store')
        self.dburi = config['dburi']
        if 'table' in config:
            self.table = config['table']
        else:
            self.table = "CustodiaSecrets"

    def get(self, key):
        query = "SELECT value from %s WHERE key=?" % self.table
        try:
            conn = sqlite3.connect(self.dburi)
            c = conn.cursor()
            r = c.execute(query, (key,))
            value = r.fetchall()
        except sqlite3.Error as err:
            log_error("Error fetching key %s: [%r]" % (key, repr(err)))
            raise CSStoreError('Error occurred while trying to get key')
        if len(value) > 0:
            return value[0][0]
        else:
            return None

    def _create(self, cur):
        create = "CREATE TABLE IF NOT EXISTS %s " \
                 "(key PRIMARY KEY UNIQUE, value)" % self.table
        cur.execute(create)

    def set(self, key, value):
        setdata = "INSERT OR REPLACE into %s VALUES (?, ?)" % self.table
        try:
            conn = sqlite3.connect(self.dburi)
            with conn:
                c = conn.cursor()
                self._create(c)
                c.execute(setdata, (key, value))
        except sqlite3.Error as err:
            log_error("Error storing key %s: [%r]" % (key, repr(err)))
            raise CSStoreError('Error occurred while trying to store key')

    def list(self, keyfilter='/'):
        search = "SELECT * FROM %s WHERE key LIKE ?" % self.table
        key = "%s%%" % (keyfilter,)
        try:
            conn = sqlite3.connect(self.dburi)
            r = conn.execute(search, (key,))
            rows = r.fetchall()
        except sqlite3.Error as err:
            log_error("Error listing (filter: %s): [%r]" % (key, repr(err)))
            raise CSStoreError('Error occurred while trying to list keys')
        if len(rows) > 0:
            value = dict()
            for row in rows:
                value[row[0]] = row[1]
            return value
        else:
            return None


import unittest
class SqliteStoreTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store = SqliteStore({'dburi': 'testdbstore.sqlite'})

    @classmethod
    def tearDownClass(self):
        try:
            os.unlink('testdbstore.sqlite')
        except OSError:
            pass

    def test_0_get_empty(self):
        with self.assertRaises(CSStoreError) as err:
            self.store.get('test')

        self.assertEqual(str(err.exception),
                         'Error occurred while trying to get key')

    def test_1_list_empty(self):
        with self.assertRaises(CSStoreError) as err:
            self.store.list('test')

        self.assertEqual(str(err.exception),
                         'Error occurred while trying to list keys')

    def test_2_set_key(self):
        self.store.set('key', 'value')
        value = self.store.get('key')
        self.assertEqual(value, 'value')

    def test_3_list_key(self):
        value = self.store.list('key')
        self.assertEqual(value, {'key': 'value'})

        value = self.store.list('k')
        self.assertEqual(value, {'key': 'value'})

        value = self.store.list('none')
        self.assertEqual(value, None)

    def test_4_multiple_keys(self):
        self.store.set('/sub1/key1', 'value11')
        self.store.set('/sub1/key2', 'value12')
        self.store.set('/sub1/key3', 'value13')
        self.store.set('/sub2/key1', 'value21')
        self.store.set('/sub2/key2', 'value22')
        self.store.set('/oth3/key1', 'value31')

        value = self.store.list()
        self.assertEqual(value, {'/sub1/key1': 'value11',
                                 '/sub1/key2': 'value12',
                                 '/sub1/key3': 'value13',
                                 '/sub2/key1': 'value21',
                                 '/sub2/key2': 'value22',
                                 '/oth3/key1': 'value31'})

        value = self.store.list('/sub')
        self.assertEqual(value, {'/sub1/key1': 'value11',
                                 '/sub1/key2': 'value12',
                                 '/sub1/key3': 'value13',
                                 '/sub2/key1': 'value21',
                                 '/sub2/key2': 'value22'})

        value = self.store.list('/sub2')
        self.assertEqual(value, {'/sub2/key1': 'value21',
                                 '/sub2/key2': 'value22'})

        value = self.store.list('/o')
        self.assertEqual(value, {'/oth3/key1': 'value31'})

        value = self.store.list('/x')
        self.assertEqual(value, None)

        value = self.store.list('/sub1/key1/')
        self.assertEqual(value, None)

        value = self.store.get('/sub1')
        self.assertEqual(value, None)

        value = self.store.get('/sub2/key1')
        self.assertEqual(value, 'value21')

        value = self.store.get('/sub%')
        self.assertEqual(value, None)
