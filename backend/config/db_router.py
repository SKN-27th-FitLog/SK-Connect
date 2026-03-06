class DatabaseRouter:
    route_app_labels = []  # data DB 사용할 앱

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "data"
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "data"
        return "default"

    def allow_migrate(self, db, app_label, **hints):
        if app_label in self.route_app_labels:
            return db == "data"
        return db == "default"