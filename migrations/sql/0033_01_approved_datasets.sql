ALTER TABLE lb.candidate_observation ADD CONSTRAINT observation_revision_context
 UNIQUE(id,revision_id,draw_id,lottery_id);

CREATE TABLE lb.dataset_policy (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL REFERENCES lb.lottery ON DELETE RESTRICT,
 version_label lb.key NOT NULL, source_keys text[] NOT NULL
 CHECK(cardinality(source_keys)>0 AND array_position(source_keys,NULL) IS NULL),
 rule_labels text[] NOT NULL CHECK(cardinality(rule_labels)>0 AND array_position(rule_labels,NULL) IS NULL),
 catalog_fingerprint lb.sha256 NOT NULL,
 policy_hash lb.sha256 NOT NULL, approved_by text NOT NULL CHECK(length(approved_by) BETWEEN 1 AND 160),
 approved_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(lottery_id,version_label), UNIQUE(id,lottery_id)
);
CREATE TRIGGER policy_immutable BEFORE UPDATE OR DELETE ON lb.dataset_policy
 FOR EACH ROW EXECUTE FUNCTION lb.append_only();

CREATE TABLE lb.approved_dataset (
 id uuid PRIMARY KEY, lottery_id uuid NOT NULL REFERENCES lb.lottery ON DELETE RESTRICT,
 policy_id uuid NOT NULL, catalog_fingerprint lb.sha256 NOT NULL,
 manifest_version text NOT NULL DEFAULT 'dataset_members_v1' CHECK(manifest_version='dataset_members_v1'),
 manifest_hash lb.sha256 NOT NULL, member_count integer NOT NULL CHECK(member_count BETWEEN 1 AND 6000),
 first_date date NOT NULL, last_date date NOT NULL CHECK(last_date>=first_date),
 status text NOT NULL CHECK(status IN ('building','approved')),
 request_key text NOT NULL UNIQUE, request_hash lb.sha256 NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), approved_at timestamptz,
 approved_by text CHECK(length(approved_by) BETWEEN 1 AND 160),
 CHECK((status='building' AND approved_at IS NULL AND approved_by IS NULL)
    OR (status='approved' AND approved_at IS NOT NULL AND approved_by IS NOT NULL)),
 UNIQUE(id,lottery_id), UNIQUE(lottery_id,policy_id,manifest_version,manifest_hash),
 FOREIGN KEY(policy_id,lottery_id) REFERENCES lb.dataset_policy(id,lottery_id) ON DELETE RESTRICT
);
CREATE TABLE lb.dataset_member (
 dataset_id uuid NOT NULL, lottery_id uuid NOT NULL, draw_id uuid NOT NULL, revision_id uuid NOT NULL,
 observation_id uuid NOT NULL, ordinal integer NOT NULL CHECK(ordinal>0),
 PRIMARY KEY(dataset_id,draw_id), UNIQUE(dataset_id,ordinal),
 FOREIGN KEY(dataset_id,lottery_id) REFERENCES lb.approved_dataset(id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(revision_id,draw_id,lottery_id) REFERENCES lb.draw_revision(id,draw_id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(observation_id,revision_id,draw_id,lottery_id)
  REFERENCES lb.candidate_observation(id,revision_id,draw_id,lottery_id) ON DELETE RESTRICT
);
CREATE INDEX dataset_member_revision ON lb.dataset_member(revision_id);
CREATE TABLE lb.dataset_decision (
 id uuid PRIMARY KEY, dataset_id uuid NOT NULL, lottery_id uuid NOT NULL,
 action text NOT NULL CHECK(action IN ('approve','reuse','activate')), actor text NOT NULL CHECK(length(actor) BETWEEN 1 AND 160),
 database_actor text NOT NULL DEFAULT current_user,
 command_key text NOT NULL UNIQUE, request_hash lb.sha256 NOT NULL,
 active_version bigint, previous_dataset_id uuid,
 decided_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK((action IN ('approve','reuse') AND active_version IS NULL AND previous_dataset_id IS NULL)
    OR (action='activate' AND active_version>0)),
 FOREIGN KEY(dataset_id,lottery_id) REFERENCES lb.approved_dataset(id,lottery_id) ON DELETE RESTRICT,
 FOREIGN KEY(previous_dataset_id,lottery_id) REFERENCES lb.approved_dataset(id,lottery_id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX dataset_single_approval ON lb.dataset_decision(dataset_id) WHERE action='approve';
CREATE UNIQUE INDEX dataset_activation_version ON lb.dataset_decision(lottery_id,active_version) WHERE action='activate';
CREATE TRIGGER dataset_decision_immutable BEFORE UPDATE OR DELETE ON lb.dataset_decision
 FOR EACH ROW EXECUTE FUNCTION lb.append_only();
CREATE TABLE lb.active_dataset (
 lottery_id uuid PRIMARY KEY REFERENCES lb.lottery ON DELETE RESTRICT, dataset_id uuid NOT NULL,
 row_version bigint NOT NULL CHECK(row_version>0),
 FOREIGN KEY(dataset_id,lottery_id) REFERENCES lb.approved_dataset(id,lottery_id) ON DELETE RESTRICT
);

CREATE FUNCTION lb.guard_dataset() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lb AS $$
BEGIN
 IF TG_OP='DELETE' OR (TG_OP='UPDATE' AND OLD.status='approved') THEN
   RAISE EXCEPTION 'approved_dataset_immutable' USING ERRCODE='23514';
 END IF;
 IF TG_OP='INSERT' AND NEW.status<>'building' THEN
   RAISE EXCEPTION 'dataset_must_start_building' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND (to_jsonb(NEW)-ARRAY['status','approved_at','approved_by'])
   IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['status','approved_at','approved_by']) THEN
   RAISE EXCEPTION 'dataset_context_immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER dataset_guard BEFORE INSERT OR UPDATE OR DELETE ON lb.approved_dataset
 FOR EACH ROW EXECUTE FUNCTION lb.guard_dataset();

CREATE FUNCTION lb.guard_dataset_member() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lb AS $$
DECLARE state text;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'dataset_member_immutable' USING ERRCODE='23514'; END IF;
 SELECT status INTO state FROM lb.approved_dataset WHERE id=NEW.dataset_id FOR UPDATE;
 IF state IS DISTINCT FROM 'building' THEN
   RAISE EXCEPTION 'approved_dataset_immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER dataset_member_guard BEFORE INSERT OR UPDATE OR DELETE ON lb.dataset_member
 FOR EACH ROW EXECUTE FUNCTION lb.guard_dataset_member();

-- Manifesto v1: slug LF policy_hash LF catalog_hash LF,
-- seguido de draw_uuid|revision_uuid|observation_uuid|YYYY-MM-DD|content_hash LF, em ordem ordinal.
CREATE FUNCTION lb.check_dataset() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lb AS $$
DECLARE d lb.approved_dataset; p lb.dataset_policy; n integer; lo date; hi date; lines text; slug text;
BEGIN
 SELECT * INTO d FROM lb.approved_dataset WHERE id=NEW.id;
 IF d.status<>'approved' THEN RAISE EXCEPTION 'dataset_not_approved' USING ERRCODE='23514'; END IF;
 SELECT * INTO p FROM lb.dataset_policy WHERE id=d.policy_id;
 SELECT l.slug INTO slug FROM lb.lottery l WHERE l.id=d.lottery_id;
 SELECT count(*),min(r.draw_date_local),max(r.draw_date_local),
   string_agg(m.draw_id::text||'|'||m.revision_id::text||'|'||m.observation_id::text||'|'||to_char(r.draw_date_local,'YYYY-MM-DD')||'|'||r.content_hash||E'\n','' ORDER BY m.ordinal)
 INTO n,lo,hi,lines FROM lb.dataset_member m JOIN lb.draw_revision r ON r.id=m.revision_id WHERE m.dataset_id=d.id;
 IF n<>d.member_count OR lo<>d.first_date OR hi<>d.last_date
   OR (SELECT max(ordinal) FROM lb.dataset_member WHERE dataset_id=d.id)<>n
   OR EXISTS(SELECT FROM lb.dataset_member m JOIN lb.draw_revision r ON r.id=m.revision_id
     JOIN lb.rule_version rv ON rv.id=r.rule_version_id
     JOIN lb.candidate_observation o ON o.id=m.observation_id
     JOIN lb.processing_run pr ON pr.id=o.processing_run_id
     JOIN lb.capture_receipt cr ON cr.id=pr.receipt_id
     JOIN lb.data_source s ON s.id=cr.source_id
     WHERE m.dataset_id=d.id AND (r.seal_state<>'sealed' OR o.decision NOT IN ('new','unchanged','correction_candidate','replayed')
       OR o.semantic_hash<>r.content_hash OR pr.status<>'completed'
       OR r.canonicalization_version NOT IN ('lottobrain.historical.result.v1','lottobrain.mega_sena.result.v1')
       OR pr.canonicalization_version<>r.canonicalization_version
       OR NOT(s.key=ANY(p.source_keys)) OR NOT(rv.version_label=ANY(p.rule_labels))
       OR s.readiness NOT IN ('approved','contract_observed')))
   OR d.manifest_hash<>encode(sha256(convert_to(slug||E'\n'||p.policy_hash||E'\n'||d.catalog_fingerprint||E'\n'||coalesce(lines,''),'UTF8')),'hex')
   OR NOT EXISTS(SELECT FROM lb.dataset_decision a WHERE a.dataset_id=d.id AND a.action='approve'
     AND a.actor=d.approved_by AND a.command_key=d.request_key AND a.request_hash=d.request_hash)
 THEN RAISE EXCEPTION 'invalid_dataset_manifest_or_members' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER dataset_complete AFTER INSERT OR UPDATE ON lb.approved_dataset
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lb.check_dataset();

CREATE FUNCTION lb.guard_active_dataset() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lb AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'active_dataset_delete_forbidden' USING ERRCODE='23514'; END IF;
 IF (TG_OP='INSERT' AND NEW.row_version<>1)
   OR (TG_OP='UPDATE' AND (NEW.lottery_id<>OLD.lottery_id OR NEW.row_version<>OLD.row_version+1))
   OR NOT EXISTS(SELECT FROM lb.approved_dataset d WHERE d.id=NEW.dataset_id AND d.lottery_id=NEW.lottery_id AND d.status='approved')
 THEN RAISE EXCEPTION 'invalid_active_dataset' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER active_dataset_guard BEFORE INSERT OR UPDATE OR DELETE ON lb.active_dataset
 FOR EACH ROW EXECUTE FUNCTION lb.guard_active_dataset();
CREATE FUNCTION lb.check_active_dataset() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,lb AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM lb.dataset_decision WHERE dataset_id=NEW.dataset_id AND lottery_id=NEW.lottery_id
   AND action='activate' AND active_version=NEW.row_version
   AND previous_dataset_id IS NOT DISTINCT FROM CASE WHEN TG_OP='UPDATE' THEN OLD.dataset_id ELSE NULL END)
 THEN RAISE EXCEPTION 'active_dataset_without_decision' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER active_dataset_decision AFTER INSERT OR UPDATE ON lb.active_dataset
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lb.check_active_dataset();

CREATE VIEW lb.approved_draw_revision WITH(security_barrier=true) AS
 SELECT m.dataset_id,m.ordinal AS dataset_ordinal,m.observation_id AS dataset_observation_id,r.*
 FROM lb.dataset_member m JOIN lb.approved_dataset d ON d.id=m.dataset_id
 JOIN lb.draw_revision r ON r.id=m.revision_id WHERE d.status='approved';
CREATE VIEW lb.approved_result_series WITH(security_barrier=true) AS
 SELECT r.dataset_id,s.* FROM lb.approved_draw_revision r JOIN lb.result_series s ON s.revision_id=r.id;
CREATE VIEW lb.approved_component_value WITH(security_barrier=true) AS
 SELECT r.dataset_id,v.* FROM lb.approved_draw_revision r JOIN lb.component_value v ON v.revision_id=r.id;
CREATE VIEW lb.approved_result_attribute WITH(security_barrier=true) AS
 SELECT r.dataset_id,a.* FROM lb.approved_draw_revision r JOIN lb.result_attribute a ON a.revision_id=r.id;
CREATE VIEW lb.approved_prize_tier_result WITH(security_barrier=true) AS
 SELECT r.dataset_id,t.* FROM lb.approved_draw_revision r JOIN lb.prize_tier_result t ON t.revision_id=r.id;
CREATE VIEW lb.approved_monetary_fact WITH(security_barrier=true) AS
 SELECT r.dataset_id,f.* FROM lb.approved_draw_revision r JOIN lb.monetary_fact f ON f.revision_id=r.id;
CREATE VIEW lb.approved_external_draw_reference WITH(security_barrier=true) AS
 SELECT DISTINCT m.dataset_id,e.draw_id,e.namespace,e.value,s.key AS source_key
 FROM lb.dataset_member m JOIN lb.approved_dataset d ON d.id=m.dataset_id
 JOIN lb.dataset_policy p ON p.id=d.policy_id
 JOIN lb.candidate_observation o ON o.revision_id=m.revision_id AND o.decision IN ('new','unchanged','correction_candidate','replayed')
 JOIN lb.external_draw_reference e ON e.evidence_observation_id=o.id AND e.draw_id=m.draw_id
 JOIN lb.data_source s ON s.id=e.source_id
 WHERE d.status='approved' AND s.key=ANY(p.source_keys);
CREATE VIEW lb.approved_dataset_info WITH(security_barrier=true) AS
 SELECT d.id,d.lottery_id,l.slug,d.manifest_version,d.manifest_hash,d.catalog_fingerprint,d.member_count,d.first_date,d.last_date,
 d.approved_at,d.approved_by,p.policy_hash,a.row_version AS active_version,(a.dataset_id=d.id) IS TRUE AS active
 FROM lb.approved_dataset d JOIN lb.lottery l ON l.id=d.lottery_id JOIN lb.dataset_policy p ON p.id=d.policy_id
 LEFT JOIN lb.active_dataset a ON a.lottery_id=d.lottery_id AND a.dataset_id=d.id WHERE d.status='approved';
