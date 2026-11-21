"""Editable clinical documentation starters; deliberately contain no medicine or dose recommendations."""
from sqlalchemy import select
from app.models.configuration import ConfigurationProfile
from app.schemas.configuration import ConfigurationProfileCreate
from app.modules.configuration.service import ConfigurationService

PRESETS = [('general-opd','General OPD'),('internal-medicine','Internal Medicine'),('pediatric','Pediatric'),('gynecology-obstetrics','Gynecology and Obstetrics'),('cardiology','Cardiology'),('orthopedic','Orthopedic'),('dermatology','Dermatology'),('ent','ENT'),('follow-up','Follow-up'),('minimal-clinic','Minimal Clinic')]


def install_presets(db,actor):
    result=[]
    has_default=db.scalar(select(ConfigurationProfile.id).where(ConfigurationProfile.branch_id==actor.branch_id,ConfigurationProfile.profile_type=='prescription_layout',ConfigurationProfile.target_id.is_(None),ConfigurationProfile.is_default.is_(True))) is not None
    for code,name in PRESETS:
        code='rx-'+code
        existing=db.scalar(select(ConfigurationProfile).where(ConfigurationProfile.branch_id==actor.branch_id,ConfigurationProfile.code==code,ConfigurationProfile.profile_type=='prescription_layout'))
        if existing:result.append(existing.id);continue
        sections=['header','patient','complaint','history','vitals','examination','diagnosis','rx','investigation','advice','follow_up','signature']
        if code=='rx-minimal-clinic':sections=['header','patient','complaint','diagnosis','rx','follow_up','signature']
        fields=[{'key':'allergies','label':'Allergies / অ্যালার্জি','type':'textarea'},{'key':'previous_medications','label':'Previous medications','type':'textarea'},{'key':'weight_kg','label':'Weight (kg) / ওজন','type':'number','min':0.1,'max':500}]
        if code=='rx-pediatric':fields+=[{'key':'date_of_birth','label':'Date of birth / জন্ম তারিখ','type':'date'},{'key':'growth_notes','label':'Growth and development','type':'textarea'}]
        if code=='rx-gynecology-obstetrics':fields+=[{'key':'obstetric_history','label':'Obstetric history','type':'textarea'},{'key':'lmp','label':'Last menstrual period','type':'date'}]
        if code=='rx-cardiology':fields+=[{'key':'cardiovascular_examination','label':'Cardiovascular examination','type':'textarea'}]
        if code=='rx-orthopedic':fields+=[{'key':'musculoskeletal_examination','label':'Musculoskeletal examination','type':'textarea'}]
        if code=='rx-dermatology':fields+=[{'key':'skin_examination','label':'Skin examination','type':'textarea'}]
        if code=='rx-ent':fields+=[{'key':'ent_examination','label':'ENT examination','type':'textarea'}]
        if code=='rx-follow-up':fields+=[{'key':'interval_history','label':'Interval history / ফলো-আপ','type':'textarea'}]
        if code=='rx-minimal-clinic':fields=fields[:1]
        row=ConfigurationService(db).create_profile(ConfigurationProfileCreate(profile_type='prescription_layout',code=code,name=name+' Prescription',scope='hospital',is_default=(code=='rx-general-opd' and not has_default),payload={'paper_size':'A5','layout':'single_column' if code=='rx-minimal-clinic' else 'two_column','font_size':11,'margin_mm':7,'sections':sections,'fields':fields,'footer_note':'Please bring this prescription on follow-up. / পরবর্তী সাক্ষাতে এই ব্যবস্থাপত্র আনুন।'}),actor)
        result.append(row.id)
    return result
