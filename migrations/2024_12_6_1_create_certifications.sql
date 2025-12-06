-- Certifications table
CREATE TABLE certifications (
    id VARCHAR(26) PRIMARY KEY,
    user_id VARCHAR(26) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'photos_pending'
        CHECK (status IN ('photos_pending', 'analyzing', 'completed', 'failed')),
    norwood_stage INTEGER CHECK (norwood_stage >= 1 AND norwood_stage <= 7),
    norwood_variant VARCHAR(5),
    confidence FLOAT,
    clinical_assessment TEXT,
    observable_features JSONB,
    differential_considerations TEXT,
    pdf_s3_key TEXT,
    certified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_certifications_user_id ON certifications(user_id);
CREATE INDEX idx_certifications_created_at ON certifications(created_at);

-- Certification photos table
CREATE TABLE certification_photos (
    id VARCHAR(26) PRIMARY KEY,
    certification_id VARCHAR(26) NOT NULL REFERENCES certifications(id) ON DELETE CASCADE,
    photo_type VARCHAR(10) NOT NULL CHECK (photo_type IN ('front', 'left', 'right')),
    s3_key TEXT NOT NULL,
    validation_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (validation_status IN ('pending', 'approved', 'rejected')),
    rejection_reason TEXT,
    quality_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (certification_id, photo_type)
);

CREATE INDEX idx_certification_photos_certification_id ON certification_photos(certification_id);
