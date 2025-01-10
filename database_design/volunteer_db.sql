CREATE TABLE auth_user (
  id           NUMBER(11) generated by default on null as identity,
  password     NVARCHAR2(128),
  last_login   TIMESTAMP(6),
  is_superuser NUMBER(1) not null,
  username     VARCHAR2(150) not null,
  first_name   NVARCHAR2(150),
  last_name    NVARCHAR2(150),
  email        NVARCHAR2(254) not null,
  is_staff     NUMBER(1) not null,
  is_active    NUMBER(1) not null,
  date_joined  TIMESTAMP(6) not null,
  is_org       NUMBER(1)  not null,
  current_login   TIMESTAMP(6)
);

CREATE TABLE languages (
  language_id NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY, -- Auto-generated ID
  language VARCHAR2(30) NOT NULL,
  CONSTRAINT languages_pk PRIMARY KEY (language_id) USING INDEX -- Primary Key with named index
);
CREATE TABLE languages_level (
  languages_level_id NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY, -- Auto-generated ID
  languages_level VARCHAR2(30) NOT NULL,
  CONSTRAINT languages_level_pk PRIMARY KEY (languages_level_id) USING INDEX -- Primary Key with named index
);

CREATE TABLE skills (
  skill_id NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY, -- Auto-generated ID
  skill_name VARCHAR2(100) NOT NULL,
  CONSTRAINT skills_pk PRIMARY KEY (skill_id) USING INDEX -- Primary Key with named index
);

CREATE TABLE profiles_org (
  profiles_org_id NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY, -- Auto-generated ID
  user_id NUMBER NOT NULL, -- Foreign Key
  org_name VARCHAR2(500) NOT NULL,
  org_web VARCHAR2(200),
  org_tel VARCHAR2(30),
  introduction VARCHAR2(500),
  profile_image_org BLOB,
  site_admin_validated VARCHAR2(1) NOT NULL,
  site_admin_approved VARCHAR2(1) NOT NULL,
  CONSTRAINT profiles_org_pk PRIMARY KEY (profiles_org_id) USING INDEX, -- Primary Key with named index
  CONSTRAINT profiles_org_fk_user FOREIGN KEY (user_id) REFERENCES auth_user(id) -- Foreign Key constraint
);

CREATE TABLE profiles_volunteer (
  profiles_vol_id NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY, -- Auto-generated ID
  user_id NUMBER NOT NULL, -- Foreign Key to auth_user.id
  birth_year NUMBER(4) NOT NULL, -- Year format
  tel VARCHAR2(30),
  job_title VARCHAR2(30),
  native_language_id NUMBER NOT NULL, -- Foreign Key
  introduction VARCHAR2(500),
  accept_recommendation VARCHAR2(1) NOT NULL, -- Mandatory
  visible_to_orgs VARCHAR2(1) NOT NULL, -- Mandatory
  willing_to_translate VARCHAR2(1) NOT NULL, -- Mandatory
  willing_to_light_physical VARCHAR2(1) NOT NULL, -- Mandatory
  profile_image_vol BLOB,
  CONSTRAINT profiles_volunteer_pk PRIMARY KEY (profiles_vol_id) USING INDEX, -- Primary Key with named index
  CONSTRAINT profiles_volunteer_fk_user FOREIGN KEY (user_id) REFERENCES auth_user(id), -- Foreign Key for user
  CONSTRAINT profiles_volunteer_fk_language FOREIGN KEY (native_language_id) REFERENCES languages(language_id) -- Foreign Key for language
);

CREATE TABLE volunteer_skills (
  vol_skill_id NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY, -- Auto-generated ID
  profiles_vol_id NUMBER NOT NULL, -- Foreign Key to profiles_volunteer.profiles_vol_id
  skill_id NUMBER NOT NULL, -- Foreign Key to skills.skill_id
  CONSTRAINT volunteer_skills_pk PRIMARY KEY (vol_skill_id) USING INDEX, -- Primary Key with named index
  CONSTRAINT volunteer_skills_fk_volunteer FOREIGN KEY (profiles_vol_id) REFERENCES profiles_volunteer(profiles_vol_id), -- Foreign Key for volunteer
  CONSTRAINT volunteer_skills_fk_skill FOREIGN KEY (skill_id) REFERENCES skills(skill_id) -- Foreign Key for skill
);

CREATE TABLE volunteer_languages (
  vol_language_id NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY, -- Auto-generated ID
  profiles_vol_id NUMBER NOT NULL, -- Foreign Key to profiles_volunteer.profiles_vol_id
  language_id NUMBER NOT NULL, -- Foreign Key to languages.language_id
  languages_level_id NUMBER NOT NULL, -- Foreign Key to languages_level.languages_level_id
  CONSTRAINT volunteer_languages_pk PRIMARY KEY (vol_language_id) USING INDEX, -- Primary Key with named index
  CONSTRAINT volunteer_languages_fk_volunteer FOREIGN KEY (profiles_vol_id) REFERENCES profiles_volunteer(profiles_vol_id), -- Foreign Key for volunteer
  CONSTRAINT volunteer_languages_fk_language FOREIGN KEY (language_id) REFERENCES languages(language_id), -- Foreign Key for language
  CONSTRAINT volunteer_languages_fk_level FOREIGN KEY (languages_level_id) REFERENCES languages_level(languages_level_id) -- Foreign Key for language level
);


CREATE TABLE events (
  event_id number NOT NULL,
  profiles_org_id number NOT NULL,
  event_name VARCHAR2(100) NOT NULL,
  event_zip number(5) NOT NULL,
  event_date date NOT NULL,
  event_description VARCHAR2(4000) NOT NULL,
  application_deadline date NOT NULL,
  event_image blob,
  CONSTRAINT events_pk PRIMARY KEY (event_id) USING INDEX,
  CONSTRAINT events_profiles_org_id_fk FOREIGN KEY (profiles_org_id) REFERENCES profiles_org(profiles_org_id)
);

CREATE TABLE event_skills (
  event_id number NOT NULL,
  skill_id number NOT NULL,
  CONSTRAINT event_skills_pk PRIMARY KEY (event_id, skill_id) USING INDEX,
  CONSTRAINT event_skills_event_fk FOREIGN KEY (event_id) REFERENCES events(event_id), 
  CONSTRAINT event_skills_skill_fk FOREIGN KEY (skill_id) REFERENCES skills(skill_id) 
);

CREATE TABLE event_translate_language (
  event_id number NOT NULL,
  target_language_id number NOT NULL,
  required_language_level_id number NOT NULL,
  CONSTRAINT event_trn_lang_pk PRIMARY KEY (event_id, target_language_id) USING INDEX,
  CONSTRAINT event_trn_lang_event_fk FOREIGN KEY (event_id) REFERENCES events(event_id), 
  CONSTRAINT event_trn_lang_fk_language FOREIGN KEY (target_language_id) REFERENCES languages(language_id), -- Foreign Key for language
  CONSTRAINT event_trn_lang_fk_level FOREIGN KEY (required_language_level_id) REFERENCES languages_level(languages_level_id) -- Foreign Key for language level
);

CREATE TABLE event_enrollment (
  event_id number NOT NULL,
  profiles_vol_id number NOT NULL,
  applied_at date NOT NULL,
  is_accepted varchar2(1),
  accepted_at date,
  is_rejected varchar2(1),
  rejected_at date,
  reject_reason varchar2(1000),
  record_created_at date NOT NULL,
  last_updated_at date,
  CONSTRAINT event_enrollment_pk PRIMARY KEY (event_id, profiles_vol_id) USING INDEX,
  CONSTRAINT event_enrollment_event_fk FOREIGN KEY (event_id) REFERENCES events(event_id), 
  CONSTRAINT event_enrollment_volunteer_fk FOREIGN KEY (profiles_vol_id) REFERENCES profiles_volunteer(profiles_vol_id) -- Foreign Key for volunteer
);

CREATE TABLE recommendations (
  recommendation_id number PRIMARY KEY NOT NULL,
  event_id number,
  from_org_id number,
  from_vol_id number,
  to_vol_id number,
  recommendation_msg varchar2(200)
);

CREATE TABLE event_chat_history (
  event_id number NOT NULL,
  from_org_id number,
  from_vol_id number,
  msg varchar2(2000),
  sent_at timestamp
);

