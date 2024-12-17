CREATE TABLE "auth_user" (
  "id" number PRIMARY KEY,
  "password" VARCHAR2(4000),
  "last_login" timestamp,
  "is_superuser" integer,
  "username" VARCHAR2(100)
);

CREATE TABLE "profiles_org" (
  "profiles_org_id" number PRIMARY KEY,
  "user_id" number NOT NULL,
  "org_name" VARCHAR2(500) NOT NULL,
  "org_email" VARCHAR2(100) NOT NULL,
  "org_web" VARCHAR2(200),
  "org_tel" VARCHAR2(30),
  "introduction" VARCHAR2(500),
  "profile_image_org" blob,
  "site_admin_validated" varchar2(1) NOT NULL
);

CREATE TABLE "profiles_volunteer" (
  "profiles_vol_id" number PRIMARY KEY,
  "user_id" number NOT NULL,
  "first_name" VARCHAR2(50) NOT NULL,
  "last_name" VARCHAR2(150) NOT NULL,
  "birth_year" number(4) NOT NULL,
  "email" VARCHAR2(100) NOT NULL,
  "tel" VARCHAR2(30),
  "job_title" VARCHAR2(30),
  "native_language_id" number NOT NULL,
  "introduction" VARCHAR2(500),
  "accept_recommendation" varchar2(1) NOT NULL,
  "visible_to_orgs" varchar2(1) NOT NULL,
  "willing_to_translate" varchar2(1) NOT NULL,
  "willing_to_light_physical" varchar2(1) NOT NULL,
  "profile_image_vol" blob
);

CREATE TABLE "languages" (
  "language_id" number PRIMARY KEY NOT NULL,
  "language" VARCHAR2(30) NOT NULL
);

CREATE TABLE "languages_level" (
  "languages_level_id" number PRIMARY KEY NOT NULL,
  "level" VARCHAR2(30) NOT NULL
);

CREATE TABLE "skills" (
  "skill_id" number PRIMARY KEY NOT NULL,
  "skill_name" VARCHAR2(100) NOT NULL
);

CREATE TABLE "volunteer_skills" (
  "vol_skill_id" number PRIMARY KEY NOT NULL,
  "profiles_vol_id" number NOT NULL,
  "skill_id" number NOT NULL
);

CREATE TABLE "volunteer_languages" (
  "vol_language_id" number PRIMARY KEY NOT NULL,
  "profiles_vol_id" number NOT NULL,
  "language_id" number NOT NULL,
  "languages_level_id" number NOT NULL
);

CREATE TABLE "events" (
  "event_id" number PRIMARY KEY NOT NULL,
  "profiles_org_id" number NOT NULL,
  "event_name" VARCHAR2(100) NOT NULL,
  "event_zip" number(5) NOT NULL,
  "event_date" date NOT NULL,
  "event_description" VARCHAR2(4000) NOT NULL,
  "application_deadline" date NOT NULL,
  "event_image" blob
);

CREATE TABLE "event_skills" (
  "event_id" number PRIMARY KEY NOT NULL,
  "skill_id" number NOT NULL
);

CREATE TABLE "event_translate_language" (
  "event_id" number PRIMARY KEY NOT NULL,
  "target_language_id" number NOT NULL,
  "required_language_level_id" number NOT NULL
);

CREATE TABLE "event_enrollment" (
  "event_id" number PRIMARY KEY NOT NULL,
  "profiles_vol_id" number NOT NULL,
  "applied_at" date NOT NULL,
  "is_accepted" varchar2(1),
  "accepted_at" date,
  "is_rejected" varchar2(1),
  "rejected_at" date,
  "reject_reason" varchar2(1000),
  "record_created_at" date NOT NULL,
  "last_updated_at" date
);

CREATE TABLE "recommendations" (
  "recommendation_id" number PRIMARY KEY NOT NULL,
  "event_id" number,
  "from_org_id" number,
  "from_vol_id" number,
  "to_vol_id" number,
  "recommendation_msg" varchar2(200)
);

CREATE TABLE "event_chat_history" (
  "event_id" number NOT NULL,
  "from_org_id" number,
  "from_vol_id" number,
  "msg" varchar2(2000),
  "sent_at" timestamp
);

ALTER TABLE "profiles_org" ADD FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id");

ALTER TABLE "profiles_volunteer" ADD FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id");

ALTER TABLE "profiles_volunteer" ADD FOREIGN KEY ("native_language_id") REFERENCES "languages" ("language_id");

ALTER TABLE "volunteer_skills" ADD FOREIGN KEY ("profiles_vol_id") REFERENCES "profiles_volunteer" ("profiles_vol_id");

ALTER TABLE "volunteer_skills" ADD FOREIGN KEY ("skill_id") REFERENCES "skills" ("skill_id");

ALTER TABLE "volunteer_languages" ADD FOREIGN KEY ("profiles_vol_id") REFERENCES "profiles_volunteer" ("profiles_vol_id");

ALTER TABLE "volunteer_languages" ADD FOREIGN KEY ("language_id") REFERENCES "languages" ("language_id");

ALTER TABLE "volunteer_languages" ADD FOREIGN KEY ("languages_level_id") REFERENCES "languages_level" ("languages_level_id");

ALTER TABLE "events" ADD FOREIGN KEY ("profiles_org_id") REFERENCES "profiles_org" ("profiles_org_id");

ALTER TABLE "event_skills" ADD FOREIGN KEY ("event_id") REFERENCES "events" ("event_id");

ALTER TABLE "event_skills" ADD FOREIGN KEY ("skill_id") REFERENCES "skills" ("skill_id");

ALTER TABLE "event_translate_language" ADD FOREIGN KEY ("event_id") REFERENCES "events" ("event_id");

ALTER TABLE "event_translate_language" ADD FOREIGN KEY ("target_language_id") REFERENCES "languages" ("language_id");

ALTER TABLE "event_translate_language" ADD FOREIGN KEY ("required_language_level_id") REFERENCES "languages_level" ("languages_level_id");

ALTER TABLE "event_enrollment" ADD FOREIGN KEY ("event_id") REFERENCES "events" ("event_id");

ALTER TABLE "event_enrollment" ADD FOREIGN KEY ("profiles_vol_id") REFERENCES "profiles_volunteer" ("profiles_vol_id");

ALTER TABLE "recommendations" ADD FOREIGN KEY ("event_id") REFERENCES "events" ("event_id");

ALTER TABLE "recommendations" ADD FOREIGN KEY ("from_org_id") REFERENCES "profiles_org" ("profiles_org_id");

ALTER TABLE "recommendations" ADD FOREIGN KEY ("from_vol_id") REFERENCES "profiles_volunteer" ("profiles_vol_id");

ALTER TABLE "recommendations" ADD FOREIGN KEY ("to_vol_id") REFERENCES "profiles_volunteer" ("profiles_vol_id");

ALTER TABLE "event_chat_history" ADD FOREIGN KEY ("event_id") REFERENCES "events" ("event_id");

ALTER TABLE "event_chat_history" ADD FOREIGN KEY ("from_org_id") REFERENCES "profiles_org" ("profiles_org_id");

ALTER TABLE "event_chat_history" ADD FOREIGN KEY ("from_vol_id") REFERENCES "profiles_volunteer" ("profiles_vol_id");
