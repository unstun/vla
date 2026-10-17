#pragma once
// Offline-only adapter. The original class/assessment names are isolated from
// the runtime atlas types; no point-cloud code links into EnvironmentalField.
void *makePointField(const char *path,const char *fnv,bool single);
void freePointField(void *field);
void pointAssessment(void *field,double x,double y,double z,double yaw,double *values);
bool pointSwitchBand(void *field,double x,double y,double z,double yaw,double hxy,double hz,double az);
