select 'create database approval' where not exists (select from pg_database where datname = 'approval')\gexec
