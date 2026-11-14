-- REQ-DATA-501: memo is not written by any client since v2; drop it.
ALTER TABLE transfers DROP COLUMN memo;
