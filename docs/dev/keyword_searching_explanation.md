# How keyword searching on collection versions works.

When a collection is imported, a row is created in the ansible_collectionversion table with metadata about the artifact.

After import, pulp_ansible runs a function to determine the highest semantic version for the related collection versions. Related rows are then updated with is_hight=True|False.

That row update triggers a postgres function to run which "tokenizes" various strings in the collection metdata, such as the namespace, name, tags and description. These tokens are weighted based on their source and the weights influence a final score when searching for a specific string ...

https://www.postgresql.org/docs/current/textsearch-controls.html

https://github.com/pulp/pulp_ansible/blob/main/pulp_ansible/app/migrations/0046_add_fulltext_search_fix.py


```sql
galaxy_ng=# select namespace,name,version,search_vector from ansible_collectionversion where namespace='zabbix';
 namespace |  name  | version |                                                             search_vector                                                             
-----------+--------+---------+---------------------------------------------------------------------------------------------------------------------------------------
 zabbix    | zabbix | 1.0.4   | 'agent':6B,10C,13 'agent2':8B 'agentd':7B 'deploy':11 'host':16 'linux':3B 'manag':15 'monitor':4B 'scale':18 'zabbix':1A,2A,5B,9C,12
(1 row)
```

When the api reduces the list of collections based on a keyword, the backend is using a filterset to call a "ts_rank" function inside postgres ...

https://github.com/pulp/pulp_ansible/blob/93e330dca8accfa438a615b6be2194c169655e7c/pulp_ansible/app/galaxy/v3/filters.py#L152-L161


Given that information, we can make a direct query to the database to simulate what the API does.

Here's a search for "zabbix" ...

```sql
galaxy_ng=# SELECT namespace,name,version
FROM ansible_collectionversion
WHERE search_vector @@ to_tsquery('english', 'zabbix')
ORDER BY ts_rank(search_vector, to_tsquery('english', 'zabbix')) DESC;

 namespace |  name  | version 
-----------+--------+---------
 zabbix    | zabbix | 1.0.4
(1 row)
```

Here's a search for "zab" ..

```sql
galaxy_ng=# SELECT namespace,name,version
FROM ansible_collectionversion
WHERE search_vector @@ to_tsquery('english', 'zab')
ORDER BY ts_rank(search_vector, to_tsquery('english', 'zab')) DESC;
 namespace | name | version 
-----------+------+---------
(0 rows)
```

Notice that there are no results for "zab". This is due to the lack of a matching token in the search_vector field for zabbix. The implication is that our search vector is not a partial string match or a typing completion tool. 
All search queries must be strings (or a tokenized version of that string) which match one of the tokenized words exactly.
