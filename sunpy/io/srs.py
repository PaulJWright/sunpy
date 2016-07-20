"""
This module implements SRS File Reader.
"""
__author__ = "Sudarshan Konge"
__email__ = "sudk1896@gmail.com"

from astropy.table import Table, Column, vstack, MaskedColumn
import collections, calendar, re

__all__ = ['read']

def read(filepath):
    """
    Method for reading an SRS File.
    """
    File = open(filepath, 'r')
    lines = list()
    for line in File:
        arr = line.split()
        store = list()
        for i in range(0, min(len(arr), 8)):
            store.append(arr[i])
        lines.append(store)

    #Store table meta-data. Only first two lines
    #of SRS text file store the meta-data.
    meta_data = collections.OrderedDict()
    regex = re.compile('[^a-zA-Z]')
    try:
        meta_data[regex.sub('', lines[0][0])] = lines[0][1]
        meta_data[regex.sub('', lines[1][0])] = ' '.join(lines[1][1:])
    except IndexError:
        print ("SRS meta-data is not available.")

    #Problem: An array of strings. We need to extract
    #three tables from these I, IA and II.

    table = list() #This table holds the three tables which we would later merge.
    indices = list()
    
    for i in range(0, len(lines)):
        if (lines[i][0][0] == 'I'):
            indices.append(i)
    indices.append(len(lines))
    indices.sort()
    
    for i in range(0, len(indices) - 1):
        cols = lines[indices[i]+1]
        temp_table = Table(names = cols, dtype=['object_']*len(cols))
        #If a table is empty, we are not adding it.
        for j in range(indices[i]+2, indices[i+1]):
            temp_string = lines[j]
            temp_array = temp_string
            if (len(temp_array) == len(cols)):
                temp_table.add_row(temp_array)
        #Make the table, data-type aware while
        #you're building it.
        #If it is empty, don't do anything
        #Just add the empty table as it is.
        if len(temp_table)>0:
            for cols in temp_table.columns.values():
                #Make the table columns unit-aware. First convert string to
                #floats, ones which can be converted that is.
                try:
                    column = temp_table[cols.name].astype(float)
                    temp_table.replace_column(cols.name, column)
                except ValueError:
                    pass
        table.append(temp_table)

    #"table" now has three different tables i.e.
    #I, IA and II.
    attributes = list() 
    
    for item in table:
        for cols in item.columns.values():
            attributes.append(cols.name)
    attributes = list(set(attributes))
    #"attributes" is for the master table.
    
    #We are adding those columns in the tables
    #that the tables don't have and initializing
    #them with 'None'.
    for item in table:
        for attrs in attributes:
            item_attr = [cols.name for cols in item.columns.values()]
            if attrs not in item_attr:
                new_column = MaskedColumn(['-']*len(item), name=attrs, dtype='object_', mask=[True]*len(item))
                item.add_column(new_column)

    #Just add a column for ID
    Map = {0:'I', 1:'IA', 2:'II'}
    #Map is for - > 0th table is I, 1st table is IA, 2nd Table is II.
    for i in range(0, len(table)):
        table[i].add_column(Column(data=[Map[i]]*len(table[i]), name='ID', dtype='object_'))
    
    attributes.insert(0, 'ID')
    master = Table(names=attributes, dtype=['object_']*len(attributes), meta=meta_data)
    #We will store all the three tables as a single table, basically
    #store all rows of all the three (or less) tables in 'master'

    #Why are we doing This ?
    #We first decide an order of the columns in the master table.
    #This order is arbitrary (choose and fix on any order you like).
    #The columns in the three (or less) tables in 'table', don't follow
    #the same order we fixed on 'master'. We need to make them. Once we
    #do that all that remains is to add all the rows to 'master'
    for items in table:
        #Take care of order of columns.
        #OrderedDict because we care about order
        #of columns.
        dict_of_columns = collections.OrderedDict()
        for columns in items.columns.values():
            dict_of_columns[columns.name] = items[columns.name]
        new_table = Table() #The re-ordered table. Ordered according to 'master'
        for cols in attributes:
            new_table.add_column(dict_of_columns[cols])
        for rows in new_table:
            master.add_row(rows)

    #Pre-process 'Location' variable.
    latsign = {'N':1, 'S':-1}
    lonsign = {'W':1, 'E':-1}
    latitude, longitude = list(), list()
    mask_arr = list()
    for value in master['Location']:
        #If value is NULL, just mask it.
        if value.__class__.__name__ == 'MaskedConstant':
            latitude.append('-'), longitude.append('-')
            mask_arr.append(True)
        else:
            lati = latsign[value[0]]*float(value[1:3])
            longi = lonsign[value[3]]*float(value[4:])
            latitude.append(lati), longitude.append(longi)
            mask_arr.append(False)

    #All columns in master are of type object_,
    #Convert them to the requisite types. The rows
    #or the column data is of the correct data type, courtesy
    #previous pre-processing, now make the column data type aware in
    #Master.
    for cols in master.columns.values():
        flag = False
        #Check if column has a floating point number.
        #Ignore masked values.
        for vals in master[cols.name]:
            if vals.__class__.__name__ != 'MaskedConstant':
                try:
                    float(vals)
                    flag = True
                except ValueError:
                    pass
        if flag:
            column = master[cols.name].astype(float)
            master.replace_column(cols.name, column)
    
    master.rename_column('Lo', 'CarringtonLong')
    master.add_column(MaskedColumn(data=latitude, name='Latitude', mask=mask_arr, unit='u.deg'))
    master.add_column(MaskedColumn(data=longitude, name='Longitude', mask=mask_arr, unit='u.deg'))
    master.remove_column('Location')
    master['Area'].unit = 'u.m**2'
    master['Lat'].unit = 'u.deg'
    master['CarringtonLong'].unit = 'u.deg'
    return master
