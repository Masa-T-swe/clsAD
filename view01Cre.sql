CREATE VIEW viewADset AS 
    SELECT ADset.ch, ADset.name, range_master.detail, ADset.valueMin, ADset.valueMax, ADset.offset, ADset.format, ADset.unit 
    FROM ADset INNER JOIN range_master ON ADset.range=range_master.range
    ORDER BY ADset.ch;
