-- Dedicated read-only login; password is provisioned out-of-band, never in Git.
create role pharmacy_agent_backend login inherit nosuperuser nobypassrls nocreatedb nocreaterole noreplication;
grant pharmacy_inventory_reader to pharmacy_agent_backend with inherit true, set true;
grant connect on database postgres to pharmacy_agent_backend;
alter role pharmacy_agent_backend set default_transaction_read_only=on;
alter role pharmacy_agent_backend set statement_timeout='5s';
alter role pharmacy_agent_backend set lock_timeout='1s';
alter role pharmacy_agent_backend set idle_in_transaction_session_timeout='5s';
