CREATE TABLE ADset (
	ch INT PRIMARY KEY NOT NULL,
	name TEXT,
	range INTEGER,
	valueMin REAL,
	valueMax REAL,
	offset REAL,
	format TEXT,
	unit TEXT
);
