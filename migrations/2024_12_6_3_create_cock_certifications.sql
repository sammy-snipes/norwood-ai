-- Cock certifications table
DROP TABLE IF EXISTS cock_certifications;

CREATE TABLE cock_certifications (
    id VARCHAR(26) PRIMARY KEY,
    user_id VARCHAR(26) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'analyzing', 'completed', 'failed')),
    s3_key TEXT,
    length_inches FLOAT,
    girth_inches FLOAT,
    size_category VARCHAR(20) CHECK (size_category IS NULL OR size_category IN ('micro', 'below_average', 'average', 'above_average', 'large', 'monster')),
    pleasure_zone VARCHAR(20) CHECK (pleasure_zone IS NULL OR pleasure_zone IN ('A', 'B', 'C', 'D', 'E')),
    pleasure_zone_label VARCHAR(50),
    description TEXT,
    confidence FLOAT,
    reference_objects_used TEXT,
    pdf_s3_key TEXT,
    certified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cock_certifications_user_id ON cock_certifications(user_id);
CREATE INDEX idx_cock_certifications_created_at ON cock_certifications(created_at);
