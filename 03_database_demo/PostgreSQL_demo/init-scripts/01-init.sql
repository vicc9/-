CREATE TABLE songs(
    id SERIAL PRIMARY KEY,
    title VARCHAR(100),
    artist VARCHAR(100),
    duration_seconds INT
);

INSERT INTO songs(title,artist,duration_seconds)
VALUES
('Imagine','John Lennon',183),
('Bohemian Rhapsody','Queen',354),
('Hotel California','Eagles',391);